"""Pydantic schemas for HTTP and WebSocket API endpoints."""
from typing import Any, Literal
from pydantic import BaseModel, Field

from credobot.crew.schemas import CrewResponse
from credobot.review.schemas import ReviewVerdict


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=20_000)
    session_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,64}$")


class AskResponse(BaseModel):
    trace_id: str
    response: CrewResponse
    review: ReviewVerdict
    cache_hit: bool
    events: list[str]
    duration_ms: float


class AddDocumentRequest(BaseModel):
    doc_id: str = Field(..., pattern=r"^[a-z0-9_]{3,64}$")
    text: str = Field(..., min_length=20, max_length=5000)


class AddDocumentResponse(BaseModel):
    trace_id: str
    doc_id: str
    chunks_added: dict[str, int]


class ErrorResponse(BaseModel):
    trace_id: str
    error: str
    detail: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"]
    mock_llm: bool
    collections: dict[str, int]
    cache: dict[str, Any]


class WSIn(BaseModel):
    query: str


class WSOut(BaseModel):
    trace_id: str
    turn: int
    response: CrewResponse | None = None
    review: ReviewVerdict | None = None
    error: str | None = None

