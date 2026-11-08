"""Tests for CrewAI 3-agent sequential crew and structured response."""
import pytest
from pydantic import ValidationError

from credobot import counters
from credobot.crew.agents import (
    COMPOSER_ROLE,
    LOOKUP_ROLE,
    RETRIEVAL_ROLE,
    build_agents,
)
from credobot.crew.crew import run_crew
from credobot.crew.schemas import CrewResponse, validate_response
from credobot.tools.loan_status import check_loan_application_status


def test_crew_has_three_agents_with_expected_tools(isolated_env):
    agents = build_agents()
    assert len(agents) == 3
    assert set(agents.keys()) == {RETRIEVAL_ROLE, LOOKUP_ROLE, COMPOSER_ROLE}

    retrieval_agent = agents[RETRIEVAL_ROLE]
    assert len(retrieval_agent.tools) == 1
    assert retrieval_agent.tools[0].name == "rag_lookup"

    lookup_agent = agents[LOOKUP_ROLE]
    assert len(lookup_agent.tools) == 1
    assert lookup_agent.tools[0].name == "check_loan_application_status"

    composer_agent = agents[COMPOSER_ROLE]
    assert len(composer_agent.tools) == 0


def test_policy_query_invokes_rag_tool(isolated_env):
    counters.reset()
    run = run_crew("What documents do I need for KYC?")

    assert run.tool_calls.get("tool.rag_lookup", 0) == 1
    assert run.tool_calls.get("tool.check_loan_application_status", 0) == 0
    assert run.response.intent == "policy"
    assert len(run.response.sources) > 0
    assert "kyc_documents" in run.response.sources
    assert run.response.record is None
    assert run.response.grounded is True


def test_status_query_invokes_lookup_tool(isolated_env):
    counters.reset()
    expected_record = check_loan_application_status("LA-1007")
    run = run_crew("What is the status of application LA-1007?")

    assert run.tool_calls.get("tool.check_loan_application_status", 0) == 1
    assert run.response.intent == "status"
    assert run.response.record is not None
    assert run.response.record.record_id == "LA-1007"
    assert run.response.record.status == expected_record["status"]
    assert run.response.escalate == expected_record["escalate"]
    assert run.response.grounded is True


def test_mixed_query_invokes_both(isolated_env):
    counters.reset()
    run = run_crew("Can I prepay my loan LA-1001 without penalty?")

    assert run.tool_calls.get("tool.rag_lookup", 0) == 1
    assert run.tool_calls.get("tool.check_loan_application_status", 0) == 1
    assert run.response.intent == "mixed"
    assert len(run.response.sources) > 0
    assert run.response.record is not None
    assert run.response.record.record_id == "LA-1001"
    assert run.response.grounded is True


def test_every_response_validates(isolated_env):
    test_queries = [
        "What is the maximum loan amount for personal loans?",
        "Status of application LA-1002 please.",
        "What is the interest rate for education loans for LA-1005?",
        "Who is the CEO of Google?",
        "Tell me about foreclosure charges on gold loans.",
    ]
    for q in test_queries:
        run = run_crew(q)
        resp = run.response
        assert isinstance(resp, CrewResponse)
        # Re-validating JSON serialization works
        revalidated = CrewResponse.model_validate_json(resp.model_dump_json())
        assert revalidated == resp


def test_invalid_payload_rejected():
    with pytest.raises(ValidationError):
        validate_response('{"answer": ""}')


def test_oos_query_unknown_intent(isolated_env):
    counters.reset()
    run = run_crew("What is the weather in Tokyo today?")
    assert run.response.intent == "unknown"
    assert "I don't know" in run.response.answer
    assert run.response.grounded is False
