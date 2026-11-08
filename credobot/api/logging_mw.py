"""JSON-Lines structured logging middleware and utilities for FastAPI."""
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
import time
from typing import Any
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from credobot import config
from credobot.guardrails.input_guard import mask_pii


class JsonlLogger:
    """Thread-safe append-only JSON-Lines writer."""

    def __init__(self, log_path: Path | None = None):
        self._path = log_path or (config.LOG_DIR / "requests.jsonl")
        self._lock = threading.Lock()

    @property
    def path(self) -> Path:
        return self._path

    def write(self, record: dict[str, Any]) -> None:
        """Write a dictionary as one JSON line."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False)
        with self._lock:
            with open(self._path, "a", encoding="utf-8", newline="\n") as f:
                f.write(line + "\n")


LOGGER = JsonlLogger()


def log_entry(**fields: Any) -> dict[str, Any]:
    """Construct structured JSON log entry, enforcing PII masking on query/text fields."""
    entry: dict[str, Any] = {
        "@timestamp": datetime.now(timezone.utc).isoformat(),
        "level": fields.get("level", "INFO"),
        "service": "credobot-api",
        "trace_id": fields.get("trace_id", ""),
        "event": fields.get("event", "http_request"),
    }

    for k, v in fields.items():
        if k in ("level", "service", "trace_id", "event"):
            continue
        # Defense-in-depth: mask any query/text string
        if isinstance(v, str) and (k.startswith("query") or k.startswith("text")):
            masked_v = mask_pii(v).text
            entry[k] = masked_v
        else:
            entry[k] = v

    return entry


class RequestLogMiddleware(BaseHTTPMiddleware):
    """HTTP middleware creating trace ID, timing requests, and writing structured JSONL."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        trace_id = request.headers.get("x-trace-id") or uuid.uuid4().hex
        request.state.trace_id = trace_id
        request.state.log_extra = {}

        t0 = time.perf_counter()
        status_code = 500
        error_msg: str | None = None

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Trace-Id"] = trace_id
            return response
        except Exception as exc:
            error_msg = str(exc)
            raise exc
        finally:
            dt_ms = (time.perf_counter() - t0) * 1000.0
            extra = dict(getattr(request.state, "log_extra", {}))
            extra.pop("duration_ms", None)
            req_error = extra.pop("error", None) or error_msg
            log_data = log_entry(
                trace_id=trace_id,
                event="http_request",
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=round(dt_ms, 2),
                error=req_error,
                **extra,
            )
            LOGGER.write(log_data)
