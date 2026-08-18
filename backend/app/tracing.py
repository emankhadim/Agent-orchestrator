

from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

TRACE_FILE = Path(__file__).resolve().parent.parent / "traces.jsonl"


def _write_span(span: dict[str, Any]) -> None:
    with TRACE_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(span, default=str) + "\n")


@contextmanager
def span(name: str, trace_id: str, attributes: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    span_id = str(uuid.uuid4())
    start = time.time()
    record: dict[str, Any] = {"attributes": attributes or {}}
    try:
        yield record
        status = "ok"
    except Exception as exc:  # noqa: BLE001 - re-raised after span is recorded
        status = "error"
        record["attributes"]["error"] = str(exc)
        raise
    finally:
        end = time.time()
        _write_span(
            {
                "trace_id": trace_id,
                "span_id": span_id,
                "name": name,
                "start_time": start,
                "end_time": end,
                "duration_ms": round((end - start) * 1000, 2),
                "status": status,
                "attributes": record["attributes"],
            }
        )
