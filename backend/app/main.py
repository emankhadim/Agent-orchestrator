from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.db import RunRecord, get_session, init_db
from app.llm import LLM_MODE
from app.models import HealthResponse, RunResult, RunStatus, RunSummary, TaskRequest
from app.orchestrator import run_task

app = FastAPI(
    title="Agentic Orchestrator API",
    description="Deterministic multi-step agent orchestration with typed contracts, "
    "a legal-transition state machine, tool calling, and structured tracing.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo only — lock this down per-environment in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", llm_mode=LLM_MODE)


@app.post("/runs", response_model=RunResult)
def create_run(request: TaskRequest) -> RunResult:
    return run_task(request)


@app.get("/runs", response_model=list[RunSummary])
def list_runs() -> list[RunSummary]:
    session = get_session()
    try:
        records = session.query(RunRecord).order_by(RunRecord.created_at.desc()).limit(50).all()
        return [
            RunSummary(
                run_id=UUID(r.run_id),
                status=RunStatus(r.status),
                query=r.query,
                created_at=r.created_at,
                step_count=len(r.steps_json or []),
            )
            for r in records
        ]
    finally:
        session.close()


@app.get("/runs/{run_id}", response_model=RunResult)
def get_run(run_id: UUID) -> RunResult:
    session = get_session()
    try:
        record = session.get(RunRecord, str(run_id))
        if record is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return RunResult(
            run_id=UUID(record.run_id),
            status=RunStatus(record.status),
            final_state=record.final_state,
            answer=record.answer,
            steps=record.steps_json,
            created_at=record.created_at,
            finished_at=record.finished_at,
        )
    finally:
        session.close()
