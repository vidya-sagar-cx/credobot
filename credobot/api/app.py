"""FastAPI application for CredoBot loan support service."""
from contextlib import asynccontextmanager
from dataclasses import asdict
import json
import time
from typing import Any
import uuid

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from credobot import config, counters
from credobot.api.logging_mw import LOGGER, RequestLogMiddleware, log_entry
from credobot.api.models import (
    AddDocumentRequest,
    AddDocumentResponse,
    AskRequest,
    AskResponse,
    ErrorResponse,
    HealthResponse,
    WSIn,
    WSOut,
)
from credobot.governance.budget import BudgetExceededError
from credobot.guardrails.input_guard import check_input
from credobot.pipeline import answer
from credobot.rag.embeddings import embed
from credobot.rag.index import COLLECTIONS, add_document, ensure_index, get_collection


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Ensure ChromaDB index exists and warm the embedding model on startup."""
    ensure_index()
    embed(["warmup sentence"])
    yield


app = FastAPI(title="CredoBot", version="0.1.0", lifespan=lifespan)
app.add_middleware(RequestLogMiddleware)


@app.post(
    "/ask",
    response_model=AskResponse,
    responses={413: {"model": ErrorResponse}},
)
def ask(req: AskRequest, request: Request) -> Any:
    """Sync HTTP endpoint running full 7-stage pipeline in a threadpool."""
    t0 = time.perf_counter()
    trace_id = getattr(request.state, "trace_id", uuid.uuid4().hex)

    try:
        result = answer(
            query=req.query,
            session_id=req.session_id,
            trace_id=trace_id,
        )
    except BudgetExceededError as exc:
        dt_ms = (time.perf_counter() - t0) * 1000.0
        request.state.log_extra = {
            "error": "budget_exceeded",
            "session_id": req.session_id,
            "duration_ms": round(dt_ms, 2),
        }
        return JSONResponse(
            status_code=413,
            content=ErrorResponse(
                trace_id=trace_id,
                error="budget_exceeded",
                detail=asdict(exc.estimate),
            ).model_dump(),
        )

    dt_ms = (time.perf_counter() - t0) * 1000.0
    request.state.log_extra = {
        "session_id": req.session_id,
        "query_masked": result.query_masked,
        "cache_hit": result.cache_hit,
        "guardrail_events": result.events,
        "intent": result.response.intent,
        "approved": result.verdict.approved,
        "duration_ms": round(dt_ms, 2),
    }

    return AskResponse(
        trace_id=result.trace_id,
        response=result.response,
        review=result.verdict,
        cache_hit=result.cache_hit,
        events=result.events,
        duration_ms=round(dt_ms, 2),
    )


@app.post(
    "/add-document",
    response_model=AddDocumentResponse,
    responses={400: {"model": ErrorResponse}},
)
def add_doc(req: AddDocumentRequest, request: Request) -> Any:
    """Add a new policy document into Chroma collections after guardrail inspection."""
    trace_id = getattr(request.state, "trace_id", uuid.uuid4().hex)

    # Check input text for prompt injection attempts
    inp_chk = check_input(req.text)
    if inp_chk.blocked:
        request.state.log_extra = {
            "error": "injection_detected",
            "guardrail_events": inp_chk.events,
        }
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                trace_id=trace_id,
                error="injection_detected",
                detail={"events": inp_chk.events},
            ).model_dump(),
        )

    counts = add_document(doc_id=req.doc_id, text=inp_chk.masked_text)
    request.state.log_extra = {
        "doc_id": req.doc_id,
        "chunks_added": counts,
        "guardrail_events": inp_chk.events,
    }

    return AddDocumentResponse(
        trace_id=trace_id,
        doc_id=req.doc_id,
        chunks_added=counts,
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return operational health status, collection counts, and cache telemetry."""
    fixed_coll = get_collection(COLLECTIONS["fixed"])
    sent_coll = get_collection(COLLECTIONS["sentence"])

    return HealthResponse(
        status="ok",
        mock_llm=bool(config.MOCK_LLM),
        collections={
            COLLECTIONS["fixed"]: fixed_coll.count(),
            COLLECTIONS["sentence"]: sent_coll.count(),
        },
        cache={
            "hits": counters.get("cache.hit"),
            "misses": counters.get("cache.miss"),
        },
    )


@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket, session_id: str | None = None) -> None:
    """WebSocket endpoint supporting multi-turn conversation with client disconnect survival."""
    await ws.accept()
    sid = session_id or uuid.uuid4().hex[:12]
    turn = 0

    try:
        while True:
            raw = await ws.receive_text()
            trace_id = uuid.uuid4().hex
            turn += 1
            t0 = time.perf_counter()

            # Parse input as JSON or plain string
            query_str = raw
            try:
                msg_obj = json.loads(raw)
                if isinstance(msg_obj, dict) and "query" in msg_obj:
                    query_str = str(msg_obj["query"])
            except Exception:
                query_str = raw

            out: WSOut
            log_extra: dict[str, Any] = {}

            try:
                res = await run_in_threadpool(
                    answer,
                    query=query_str,
                    session_id=sid,
                    trace_id=trace_id,
                )
                out = WSOut(
                    trace_id=trace_id,
                    turn=turn,
                    response=res.response,
                    review=res.verdict,
                    error=None,
                )
                log_extra = {
                    "query_masked": res.query_masked,
                    "cache_hit": res.cache_hit,
                    "guardrail_events": res.events,
                    "intent": res.response.intent,
                    "approved": res.verdict.approved,
                }
            except BudgetExceededError as exc:
                out = WSOut(
                    trace_id=trace_id,
                    turn=turn,
                    response=None,
                    review=None,
                    error=f"budget_exceeded: {exc}",
                )
                log_extra = {"error": "budget_exceeded"}
            except Exception as exc:
                out = WSOut(
                    trace_id=trace_id,
                    turn=turn,
                    response=None,
                    review=None,
                    error=str(exc),
                )
                log_extra = {"error": str(exc)}

            dt_ms = (time.perf_counter() - t0) * 1000.0
            LOGGER.write(
                log_entry(
                    event="ws_message",
                    trace_id=trace_id,
                    session_id=sid,
                    turn=turn,
                    duration_ms=round(dt_ms, 2),
                    **log_extra,
                )
            )

            await ws.send_text(out.model_dump_json())

    except WebSocketDisconnect as disc:
        LOGGER.write(
            log_entry(
                event="ws_disconnect",
                session_id=sid,
                code=disc.code,
            )
        )
        return
    except Exception as exc:
        LOGGER.write(
            log_entry(
                level="ERROR",
                event="ws_error",
                session_id=sid,
                error=str(exc),
            )
        )
        try:
            await ws.close(code=1011)
        except Exception:
            pass

