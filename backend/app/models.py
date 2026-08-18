from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StrictModel(BaseModel):
    """Base class: reject unknown fields, validate on assignment."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True, str_strip_whitespace=True)


class AgentState(str, Enum):
    INTAKE = "intake"
    PLANNING = "planning"
    TOOL_EXECUTION = "tool_execution"
    VALIDATION = "validation"
    COMPLETE = "complete"
    FAILED = "failed"


class ToolName(str, Enum):
    CALCULATOR = "calculator"
    KNOWLEDGE_BASE_SEARCH = "knowledge_base_search"
    WEB_SEARCH = "web_search"





class ToolCall(StrictModel):
    id: UUID = Field(default_factory=uuid4)
    tool: ToolName
    arguments: dict[str, Any]
    requested_at: datetime = Field(default_factory=utcnow)


class ToolResult(StrictModel):
    call_id: UUID
    tool: ToolName
    success: bool
    output: str
    error: str | None = None
    completed_at: datetime = Field(default_factory=utcnow)


class TaskRequest(StrictModel):
    """What a caller submits to the orchestrator."""

    query: str = Field(min_length=1, max_length=2000)
    max_steps: int = Field(default=6, ge=1, le=20)


class StepLog(StrictModel):
    step_index: int
    from_state: AgentState
    to_state: AgentState
    reasoning: str
    tool_call: ToolCall | None = None
    tool_result: ToolResult | None = None
    timestamp: datetime = Field(default_factory=utcnow)


class RunStatus(str, Enum):
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class RunResult(StrictModel):
    run_id: UUID
    status: RunStatus
    final_state: AgentState
    answer: str | None = None
    steps: list[StepLog]
    created_at: datetime
    finished_at: datetime | None = None


class RunSummary(StrictModel):
    """Lightweight projection returned by list endpoints."""

    run_id: UUID
    status: RunStatus
    query: str
    created_at: datetime
    step_count: int


class HealthResponse(StrictModel):
    status: Literal["ok"]
    llm_mode: Literal["live", "demo_fallback"]
