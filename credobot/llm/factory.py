"""Factory for creating LLM clients (MockLLM vs real OpenAI-compatible)."""
import os
from typing import Any, Callable
from credobot import config
from credobot.llm.mock_llm import MockLLM


def get_crew_llm() -> Any:
    """Return configured LLM for CrewAI agents."""
    if config.MOCK_LLM:
        return MockLLM()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required when MOCK_LLM=false")
    from crewai import LLM

    return LLM(
        model=config.LLM_MODEL,
        base_url=config.OPENAI_BASE_URL,
        api_key=api_key,
        temperature=0,
    )


def get_text_llm() -> Callable[[str], str]:
    """Return a callable that takes a string prompt and returns generated text."""
    if config.MOCK_LLM:

        def _mock_raise(_prompt: str) -> str:
            raise RuntimeError(
                "get_text_llm is only available when MOCK_LLM=false; mock mode uses extractive generation."
            )

        return _mock_raise

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required when MOCK_LLM=false")
    from crewai import LLM

    llm = LLM(
        model=config.LLM_MODEL,
        base_url=config.OPENAI_BASE_URL,
        api_key=api_key,
        temperature=0,
    )
    return lambda prompt: str(llm.call(prompt))


def get_autogen_client(role: str = "reviewer") -> Any:
    """Return client for Autogen review team."""
    if config.MOCK_LLM:
        from credobot.review.mock_client import MockReviewClient

        return MockReviewClient(role=role)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required when MOCK_LLM=false")
    from autogen_ext.models.openai import OpenAIChatCompletionClient

    return OpenAIChatCompletionClient(
        model=config.LLM_MODEL,
        base_url=config.OPENAI_BASE_URL,
        api_key=api_key,
    )
