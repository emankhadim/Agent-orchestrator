
from __future__ import annotations

from app.models import AgentState

# Explicit legal-transition table. Any transition not listed here is
# rejected by `assert_transition`, regardless of what the LLM proposes.
_ALLOWED_TRANSITIONS: dict[AgentState, set[AgentState]] = {
    AgentState.INTAKE: {AgentState.PLANNING, AgentState.FAILED},
    AgentState.PLANNING: {AgentState.TOOL_EXECUTION, AgentState.VALIDATION, AgentState.FAILED},
    AgentState.TOOL_EXECUTION: {AgentState.PLANNING, AgentState.VALIDATION, AgentState.FAILED},
    AgentState.VALIDATION: {AgentState.COMPLETE, AgentState.PLANNING, AgentState.FAILED},
    AgentState.COMPLETE: set(),
    AgentState.FAILED: set(),
}


class IllegalTransitionError(Exception):
    def __init__(self, from_state: AgentState, to_state: AgentState) -> None:
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Illegal transition: {from_state.value} -> {to_state.value}. "
            f"Allowed from {from_state.value}: "
            f"{sorted(s.value for s in _ALLOWED_TRANSITIONS[from_state])}"
        )


def assert_transition(from_state: AgentState, to_state: AgentState) -> None:
    """Raise IllegalTransitionError if the proposed move isn't in the table."""
    if to_state not in _ALLOWED_TRANSITIONS[from_state]:
        raise IllegalTransitionError(from_state, to_state)


def is_terminal(state: AgentState) -> bool:
    return state in (AgentState.COMPLETE, AgentState.FAILED)
