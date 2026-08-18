from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app import llm, tracing
from app.db import RunRecord, get_session
from app.models import AgentState, RunResult, RunStatus, StepLog, TaskRequest
from app.state_machine import assert_transition, is_terminal
from app.tools import execute_tool


def run_task(request: TaskRequest) -> RunResult:
    run_id = uuid4()
    trace_id = str(run_id)
    created_at = datetime.now(timezone.utc)

    state = AgentState.INTAKE
    steps: list[StepLog] = []
    history_summary = ""
    final_answer: str | None = None

    with tracing.span("run", trace_id, {"query": request.query}):
        for step_index in range(request.max_steps):
            if is_terminal(state):
                break

            with tracing.span("propose_next_step", trace_id, {"state": state.value}) as s:
                proposal = llm.propose_next_step(request.query, state, history_summary)
                s["attributes"]["proposed_next_state"] = proposal.next_state.value

            assert_transition(state, proposal.next_state)

            tool_call = None
            tool_result = None
            if proposal.tool is not None:
                from app.models import ToolCall

                tool_call = ToolCall(tool=proposal.tool, arguments=proposal.tool_arguments or {})
                with tracing.span("tool_call", trace_id, {"tool": proposal.tool.value}) as s:
                    tool_result = execute_tool(tool_call)
                    s["attributes"]["success"] = tool_result.success
                history_summary += f"\n[{proposal.tool.value}] -> {tool_result.output}"

            steps.append(
                StepLog(
                    step_index=step_index,
                    from_state=state,
                    to_state=proposal.next_state,
                    reasoning=proposal.reasoning,
                    tool_call=tool_call,
                    tool_result=tool_result,
                )
            )

            state = proposal.next_state
            if proposal.final_answer:
                final_answer = proposal.final_answer

            if state == AgentState.VALIDATION:
                # Deterministic validation gate: a run only reaches COMPLETE if
                # we actually have an answer. Otherwise it's kicked back to
                # PLANNING rather than silently completing empty-handed.
                next_state = AgentState.COMPLETE if final_answer else AgentState.PLANNING
                assert_transition(state, next_state)
                steps.append(
                    StepLog(
                        step_index=step_index + 1,
                        from_state=state,
                        to_state=next_state,
                        reasoning="Validation gate: answer present." if final_answer else "Validation gate: no answer yet, replanning.",
                    )
                )
                state = next_state

    status = RunStatus.COMPLETE if state == AgentState.COMPLETE else RunStatus.FAILED
    finished_at = datetime.now(timezone.utc)

    result = RunResult(
        run_id=run_id,
        status=status,
        final_state=state,
        answer=final_answer,
        steps=steps,
        created_at=created_at,
        finished_at=finished_at,
    )

    session = get_session()
    try:
        session.add(
            RunRecord(
                run_id=str(run_id),
                query=request.query,
                status=status.value,
                final_state=state.value,
                answer=final_answer,
                steps_json=[step.model_dump(mode="json") for step in steps],
                created_at=created_at,
                finished_at=finished_at,
            )
        )
        session.commit()
    finally:
        session.close()

    return result
