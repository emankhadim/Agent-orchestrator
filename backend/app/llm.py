
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from app.models import AgentState, ToolName

LLM_MODE = "live" if os.environ.get("ANTHROPIC_API_KEY") else "demo_fallback"


@dataclass
class Proposal:
    next_state: AgentState
    reasoning: str
    tool: ToolName | None = None
    tool_arguments: dict | None = None
    final_answer: str | None = None


def propose_next_step(query: str, current_state: AgentState, history_summary: str) -> Proposal:
    """Return the model's proposed next step. Never mutates state directly —
    the caller (orchestrator) is responsible for validating and applying it
    via state_machine.assert_transition().
    """
    if LLM_MODE == "live":
        return _propose_via_litellm(query, current_state, history_summary)
    return _propose_demo_fallback(query, current_state, history_summary)


def _propose_via_litellm(query: str, current_state: AgentState, history_summary: str) -> Proposal:
    import litellm  # imported lazily so demo mode never requires the package

    system = (
        "You are a planning module inside a deterministic agent orchestrator. "
        "You NEVER control state transitions directly — you only propose one of: "
        "'use_tool:<calculator|knowledge_base_search|web_search>' or 'finish'. "
        "Reply with exactly one line in that format, followed by a short reasoning line."
    )
    response = litellm.completion(
        model="claude-sonnet-4-6",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Query: {query}\nProgress so far: {history_summary}"},
        ],
        max_tokens=200,
    )
    text = response.choices[0].message.content or ""
    return _parse_llm_reply(text, current_state, query)


def _parse_llm_reply(text: str, current_state: AgentState, query: str) -> Proposal:
    if "finish" in text.lower():
        return Proposal(next_state=AgentState.VALIDATION, reasoning=text.strip(), final_answer=text)
    match = re.search(r"use_tool:(\w+)", text)
    if match:
        tool = ToolName(match.group(1))
        return Proposal(
            next_state=AgentState.TOOL_EXECUTION,
            reasoning=text.strip(),
            tool=tool,
            tool_arguments={"query": query, "expression": query},
        )
    return Proposal(next_state=AgentState.VALIDATION, reasoning="Unparseable reply; finishing.", final_answer=text)


def _propose_demo_fallback(query: str, current_state: AgentState, history_summary: str) -> Proposal:
    """Deterministic stand-in planner used when no LLM API key is configured.

    Still exercises the full state machine + tool + tracing pipeline —
    only the "which action to take" decision is rule-based instead of
    model-based.
    """
    looks_like_math = bool(re.fullmatch(r"[\d\s\+\-\*/\.\(\)]+", query.strip()))

    if current_state == AgentState.INTAKE:
        return Proposal(next_state=AgentState.PLANNING, reasoning="Intake complete; moving to planning.")

    if current_state == AgentState.PLANNING:
        if looks_like_math:
            return Proposal(
                next_state=AgentState.TOOL_EXECUTION,
                reasoning="Query looks numeric; delegating to the calculator tool.",
                tool=ToolName.CALCULATOR,
                tool_arguments={"expression": query},
            )
        return Proposal(
            next_state=AgentState.TOOL_EXECUTION,
            reasoning="Query looks like a knowledge question; searching the knowledge base.",
            tool=ToolName.KNOWLEDGE_BASE_SEARCH,
            tool_arguments={"query": query},
        )

    if current_state == AgentState.TOOL_EXECUTION:
        return Proposal(
            next_state=AgentState.VALIDATION,
            reasoning="Tool call returned; moving to validation.",
            final_answer=history_summary,
        )

    return Proposal(next_state=AgentState.VALIDATION, reasoning="Defaulting to validation.", final_answer=history_summary)
