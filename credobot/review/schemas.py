"""Structured output schema for the AutoGen review stage."""
from pydantic import BaseModel, Field


class ReviewVerdict(BaseModel):
    approved: bool = Field(..., description="Whether the draft answer was approved unchanged.")
    final_answer: str = Field(..., description="The verified final answer text.")
    reason: str = Field(..., description="Detailed explanation of findings or removals.")
