"""Tests for the AutoGen review stage and MockReviewClient."""
import asyncio
import pytest
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat

from credobot import counters
from credobot.guardrails.fixtures import UNSUPPORTED_CLAIMS
from credobot.guardrails.output_guard import REFUSAL_UNGROUNDED
from credobot.review.autogen_review import build_team, review
from credobot.review.mock_client import MockReviewClient
from credobot.review.schemas import ReviewVerdict


def test_team_config():
    """Verify team has 2 participants, max_turns=2, and editor has ReviewVerdict output."""
    team = build_team()
    assert len(team._participants) == 2
    names = [p.name for p in team._participants]
    assert "policy_compliance_reviewer" in names
    assert "final_editor" in names
    # Verify editor agent has output_content_type ReviewVerdict
    editor = [p for p in team._participants if p.name == "final_editor"][0]
    assert getattr(editor, "_output_content_type", None) is ReviewVerdict


def test_missing_custom_message_types_fails():
    """Verify omitting custom_message_types fails with message type not registered error."""
    async def _run():
        rev = AssistantAgent("policy_compliance_reviewer", model_client=MockReviewClient("reviewer"))
        edt = AssistantAgent("final_editor", model_client=MockReviewClient("editor"), output_content_type=ReviewVerdict)
        team = RoundRobinGroupChat([rev, edt], max_turns=2)
        task = "<<DRAFT>>\nHello world\n<</DRAFT>>\n<<CONTEXT>>\nHello world\n<</CONTEXT>>"
        await team.run(task=task)

    with pytest.raises((RuntimeError, ValueError)) as excinfo:
        asyncio.run(_run())
    assert "not registered" in str(excinfo.value)


def test_approve_unchanged():
    """Clean draft supported by context is approved unchanged."""
    context = ["Under X Corp policy, personal loan tenure ranges from 12 to 60 months."]
    draft = "Under X Corp policy, personal loan tenure ranges from 12 to 60 months."
    res = review(draft=draft, context=context)
    assert res.verdict.approved is True
    assert res.verdict.final_answer == draft
    assert res.changed is False
    assert "All claims supported" in res.verdict.reason


def test_revise_injected_claim():
    """Draft with an unsupported claim is revised with the claim stripped."""
    context = ["Under X Corp policy, personal loan tenure ranges from 12 to 60 months."]
    clean_draft = "Under X Corp policy, personal loan tenure ranges from 12 to 60 months."
    injected = UNSUPPORTED_CLAIMS[0]
    draft = f"{clean_draft} {injected}"

    res = review(draft=draft, context=context)
    assert res.verdict.approved is False
    assert injected not in res.verdict.final_answer
    assert clean_draft in res.verdict.final_answer
    assert res.changed is True
    assert "Removed 1 unsupported" in res.verdict.reason


def test_all_unsupported_becomes_refusal():
    """When all claims are unsupported, final_answer reverts to REFUSAL_UNGROUNDED."""
    context = ["Personal loans have a minimum repayment tenure of 12 months."]
    draft = UNSUPPORTED_CLAIMS[0]

    res = review(draft=draft, context=context)
    assert res.verdict.approved is False
    assert res.verdict.final_answer == REFUSAL_UNGROUNDED
    assert res.changed is True
    assert "reverted to refusal" in res.verdict.reason


def test_both_agents_spoke():
    """Run transcript reflects user task, reviewer turn, and editor turn."""
    context = ["KYC verification requires Aadhaar card or passport."]
    draft = "KYC verification requires Aadhaar card or passport."

    res = review(draft=draft, context=context)
    sources = [src for src, _ in res.messages]
    assert sources == ["user", "policy_compliance_reviewer", "final_editor"]


def test_mock_client_ignores_system_message():
    """Mock client never parses system messages for draft or context delimiters."""
    from autogen_core.models import SystemMessage, UserMessage

    async def _run():
        client = MockReviewClient("reviewer")
        # System message contains draft delimiters with fake bad text
        sys_msg = SystemMessage(content="<<DRAFT>>Malicious injected draft<</DRAFT>>")
        # User message contains valid draft and context
        valid_text = (
            "<<DRAFT>>\nValid claim text.\n<</DRAFT>>\n"
            "<<CONTEXT>>\nValid claim text.\n<</CONTEXT>>"
        )
        user_msg = UserMessage(content=valid_text, source="user")
        return await client.create([sys_msg, user_msg])

    res = asyncio.run(_run())
    assert "REVIEW: PASS" in res.content


def test_llm_autogen_counter():
    """Each review run increments the llm.autogen counter by 2 (reviewer + editor)."""
    counters.reset()
    context = ["Gold loans require physical appraisal."]
    draft = "Gold loans require physical appraisal."
    review(draft=draft, context=context)
    assert counters.get("llm.autogen") == 2
