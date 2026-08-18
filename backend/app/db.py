"""
Persistence layer. SQLite for zero-setup local runs; the schema uses only
portable SQLAlchemy types, so pointing DATABASE_URL at Postgres in
production is a one-line config change, not a rewrite.
"""

from __future__ import annotations

import os
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./orchestrator.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class RunRecord(Base):
    __tablename__ = "runs"

    run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    query: Mapped[str] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(String(20))
    final_state: Mapped[str] = mapped_column(String(20))
    answer: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    steps_json: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    return SessionLocal()
