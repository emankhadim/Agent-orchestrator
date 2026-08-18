
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field

VECTOR_DIM = 256


def _embed(text: str) -> list[float]:
    vec = [0.0] * VECTOR_DIM
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        idx = int(hashlib.md5(token.encode()).hexdigest(), 16) % VECTOR_DIM
        vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


@dataclass
class _Point:
    text: str
    vector: list[float] = field(default_factory=list)


class InMemoryVectorStore:
    """Drop-in stand-in for a Qdrant collection."""

    def __init__(self) -> None:
        self._points: list[_Point] = []

    def upsert(self, texts: list[str]) -> None:
        for text in texts:
            self._points.append(_Point(text=text, vector=_embed(text)))

    def search(self, query: str, top_k: int = 3) -> list[tuple[str, float]]:
        query_vec = _embed(query)
        scored = [(p.text, _cosine(query_vec, p.vector)) for p in self._points]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]


# Seed knowledge base — stand-in for BMW-style internal documentation.
knowledge_base = InMemoryVectorStore()
knowledge_base.upsert(
    [
        "The orchestrator uses a deterministic state machine: INTAKE, PLANNING, "
        "TOOL_EXECUTION, VALIDATION, COMPLETE, FAILED. The LLM proposes transitions; "
        "the state machine enforces which ones are legal.",
        "Available tools are calculator, knowledge_base_search, and web_search. "
        "Tool calls and results are logged as structured trace spans.",
        "LLM calls are routed through a provider-agnostic completion layer so the "
        "underlying model (Claude, GPT, or a local/self-hosted model) can be swapped "
        "without touching orchestration logic.",
        "Every run persists its full step history — state transitions, tool calls, "
        "and reasoning — to the database for auditability.",
    ]
)
