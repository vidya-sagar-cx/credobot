"""Structured output schemas for CredoBot CrewAI responses."""
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class LoanStatus(BaseModel):
    record_id: str
    category: str
    status: str
    loan_amount_inr: int
    days_since_created: int
    flagged_for_fraud_review: bool
    escalation_score: float = Field(ge=0, le=1)
    escalate: bool


Intent = Literal["policy", "status", "mixed", "refused", "unknown"]


class CrewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str = Field(min_length=1)
    intent: Intent
    sources: list[str] = Field(default_factory=list)
    record: LoanStatus | None = None
    escalate: bool = False
    grounded: bool
    top_similarity: float | None = None
    guardrail_events: list[str] = Field(default_factory=list)


def validate_response(raw: Any) -> CrewResponse:
    """Single validation entry point used across crew, pipeline, and API."""
    if isinstance(raw, CrewResponse):
        return raw
    if isinstance(raw, BaseModel):
        return CrewResponse.model_validate(raw.model_dump())
    if isinstance(raw, dict):
        return CrewResponse.model_validate(raw)
    if isinstance(raw, str):
        clean = raw.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        elif clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()
        return CrewResponse.model_validate_json(clean)
    raise ValueError(f"Unsupported payload type for validate_response: {type(raw)}")
