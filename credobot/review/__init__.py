"""Autogen review stage package."""
from typing import TYPE_CHECKING

from credobot.review.schemas import ReviewVerdict

if TYPE_CHECKING:
    from credobot.review.autogen_review import (
        ReviewResult,
        areview,
        build_team,
        format_review_task,
        review,
    )


def __getattr__(name: str):
    if name in ("ReviewResult", "areview", "build_team", "format_review_task", "review"):
        import credobot.review.autogen_review as ar

        return getattr(ar, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ReviewVerdict",
    "ReviewResult",
    "build_team",
    "format_review_task",
    "areview",
    "review",
]
