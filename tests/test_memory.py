"""Unit and integration tests for LangChain in-process session memory and coreference resolution."""
import pytest
from langchain_core.messages import AIMessage, HumanMessage

from credobot.memory import (
    chat,
    clear_all_sessions,
    get_session_history,
    reset_session,
    resolve_followup,
)


@pytest.fixture(autouse=True)
def _clean_sessions():
    clear_all_sessions()
    yield
    clear_all_sessions()


def test_resolve_followup_unit():
    # 1. Pronoun resolution via additional_kwargs
    history_with_kwarg = [
        HumanMessage(content="Check my application"),
        AIMessage(content="Status report", additional_kwargs={"record_id": "LA-1005"}),
    ]
    res1 = resolve_followup("What is its loan amount?", history_with_kwarg)
    assert res1.used_memory is True
    assert "LA-1005" in res1.resolved
    assert "LA-1005" in res1.note

    # 2. Pronoun resolution via text match
    history_with_text = [
        HumanMessage(content="Is LA-1009 approved?"),
        AIMessage(content="Application LA-1009 is Approved."),
    ]
    res2 = resolve_followup("Is it escalated to operations?", history_with_text)
    assert res2.used_memory is True
    assert "LA-1009" in res2.resolved

    # 3. Pronoun unresolved when history has no record ID
    empty_history = []
    res3 = resolve_followup("What is its loan amount?", empty_history)
    assert res3.used_memory is False
    assert res3.resolved == "What is its loan amount?"

    # 4. Meta question first
    history_meta = [
        HumanMessage(content="What are the KYC rules?"),
        AIMessage(content="Here are the KYC rules..."),
        HumanMessage(content="Can I prepay?"),
        AIMessage(content="Yes, prepayment is permitted..."),
    ]
    res4 = resolve_followup("What did I first ask?", history_meta)
    assert res4.used_memory is True
    assert "What are the KYC rules?" in res4.resolved

    # 5. Meta question last
    res5 = resolve_followup("What did I last ask?", history_meta)
    assert res5.used_memory is True
    assert "Can I prepay?" in res5.resolved

    # 6. Meta question on empty history
    res6 = resolve_followup("What did I first ask?", [])
    assert res6.used_memory is True
    assert "start of our conversation" in res6.resolved

    # 7. Self-contained query
    res7 = resolve_followup("What is the status of application LA-1001?", history_meta)
    assert res7.used_memory is False
    assert res7.resolved == "What is the status of application LA-1001?"


def test_history_grows_per_turn():
    sid = "test-growth-session"
    assert len(get_session_history(sid).messages) == 0

    _, res1 = chat("What is the status of application LA-1007?", sid)
    assert len(get_session_history(sid).messages) == 2

    _, res2 = chat("What is its loan amount and is it escalated?", sid)
    assert len(get_session_history(sid).messages) == 4

    _, res3 = chat("What did I first ask?", sid)
    assert len(get_session_history(sid).messages) == 6


def test_followup_resolves_record_id_within_session():
    sid = "test-coref-session"
    # Turn 1
    resp1, res1 = chat("What is the status of application LA-1007?", sid)
    assert res1.used_memory is False
    assert resp1.record is not None
    assert resp1.record.record_id == "LA-1007"

    # Turn 2: uses pronoun "its" and "it"
    resp2, res2 = chat("What is its loan amount and is it escalated?", sid)
    assert res2.used_memory is True
    assert "LA-1007" in res2.resolved
    assert resp2.record is not None
    assert resp2.record.record_id == "LA-1007"
    assert resp2.record.loan_amount_inr == 3133000
    assert resp2.record.escalate is True


def test_fresh_session_has_no_state():
    sid = "test-fresh-session"
    # Calling pronoun query with zero history
    resp, res = chat("What is its loan amount and is it escalated?", sid)
    assert res.used_memory is False
    assert resp.record is None
    assert resp.intent == "unknown"


def test_sessions_isolated():
    sid_a = "session-alice"
    sid_b = "session-bob"

    # Alice sets context with LA-1007
    chat("What is the status of application LA-1007?", sid_a)

    # Bob asks pronoun query in his own session
    resp_b, res_b = chat("What is its loan amount and is it escalated?", sid_b)
    assert res_b.used_memory is False
    assert resp_b.record is None
    assert "LA-1007" not in res_b.resolved


def test_reset_session_clears():
    sid = "test-reset-session"
    chat("What is the status of application LA-1007?", sid)
    assert len(get_session_history(sid).messages) == 2

    reset_session(sid)
    assert len(get_session_history(sid).messages) == 0

    # Next turn has no memory
    resp, res = chat("What is its loan amount and is it escalated?", sid)
    assert res.used_memory is False
    assert resp.record is None


def test_what_did_i_ask_first():
    sid = "test-meta-session"
    q1 = "What documents do I need for KYC?"
    chat(q1, sid)

    resp2, res2 = chat("What did I first ask?", sid)
    assert res2.used_memory is True
    assert q1 in resp2.answer

