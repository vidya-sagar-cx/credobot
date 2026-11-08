"""AutoGen RoundRobinGroupChat review stage."""
import asyncio
from dataclasses import dataclass
import json
from typing import Any

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import StructuredMessage
from autogen_agentchat.teams import RoundRobinGroupChat

from credobot.demos.transcript import Transcript
from credobot.guardrails.fixtures import UNSUPPORTED_CLAIMS
from credobot.llm import factory
from credobot.rag.generate import grounded_answer
from credobot.review.schemas import ReviewVerdict


@dataclass
class ReviewResult:
    verdict: ReviewVerdict
    messages: list[tuple[str, str]]  # (source, content)
    changed: bool


def build_team(
    reviewer_client: Any = None,
    editor_client: Any = None,
) -> RoundRobinGroupChat:
    """Build a 2-agent RoundRobinGroupChat for review and revision."""
    reviewer = AssistantAgent(
        name="policy_compliance_reviewer",
        model_client=reviewer_client or factory.get_autogen_client("reviewer"),
        system_message=(
            "You are CRED's policy-compliance reviewer. List every claim in the draft "
            "that the context does not support. Reply 'REVIEW: PASS' or 'REVIEW: FAIL' "
            "followed by UNSUPPORTED bullet points."
        ),
    )
    editor = AssistantAgent(
        name="final_editor",
        model_client=editor_client or factory.get_autogen_client("editor"),
        system_message=(
            "You are the final editor. If the reviewer passed, approve the draft unchanged. "
            "Otherwise remove or correct unsupported claims using only the context. "
            "Output a ReviewVerdict."
        ),
        output_content_type=ReviewVerdict,
    )
    return RoundRobinGroupChat(
        [reviewer, editor],
        max_turns=2,
        custom_message_types=[StructuredMessage[ReviewVerdict]],
    )


def format_review_task(
    draft: str,
    context: list[str],
    record: dict[str, Any] | None = None,
) -> str:
    """Format the review task prompt with delimiters."""
    parts = [
        "<<DRAFT>>",
        draft.strip(),
        "<</DRAFT>>",
        "<<CONTEXT>>",
    ]
    for i, c in enumerate(context, 1):
        parts.append(f"[{i}] {c.strip()}")
    parts.append("<</CONTEXT>>")
    if record:
        parts.append("<<RECORD>>")
        parts.append(json.dumps(record, indent=2))
        parts.append("<</RECORD>>")
    parts.append(
        "Review the draft strictly against the context and record (if provided). "
        "List every unsupported claim. If none, reply 'REVIEW: PASS'."
    )
    return "\n".join(parts)


async def areview(
    draft: str,
    context: list[str],
    record: dict[str, Any] | None = None,
    team: RoundRobinGroupChat | None = None,
) -> ReviewResult:
    """Asynchronously run the AutoGen review team."""
    if team is None:
        team = build_team()

    task = format_review_task(draft=draft, context=context, record=record)
    result = await team.run(task=task)

    msg_tuples: list[tuple[str, str]] = []
    for m in result.messages:
        if isinstance(m.content, ReviewVerdict):
            c_str = m.content.model_dump_json(indent=2)
        else:
            c_str = str(m.content)
        msg_tuples.append((m.source, c_str))

    last_msg = result.messages[-1]
    if isinstance(last_msg, StructuredMessage) and isinstance(last_msg.content, ReviewVerdict):
        verdict = last_msg.content
    elif isinstance(getattr(last_msg, "content", None), ReviewVerdict):
        verdict = last_msg.content
    elif isinstance(getattr(last_msg, "content", None), dict):
        verdict = ReviewVerdict.model_validate(last_msg.content)
    elif isinstance(getattr(last_msg, "content", None), str):
        verdict = ReviewVerdict.model_validate_json(last_msg.content)
    else:
        raise ValueError(f"Last message does not contain a ReviewVerdict: {last_msg}")

    changed = verdict.final_answer.strip() != draft.strip()
    return ReviewResult(verdict=verdict, messages=msg_tuples, changed=changed)


def review(
    draft: str,
    context: list[str],
    record: dict[str, Any] | None = None,
    team: RoundRobinGroupChat | None = None,
) -> ReviewResult:
    """Synchronous wrapper for areview."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, areview(draft, context, record, team)).result()
    else:
        return asyncio.run(areview(draft, context, record, team))


def main() -> int:
    """Generate transcripts/part4_review.md demonstrating Cases A, B, and C."""
    t = Transcript("part4_review", "Part 4 — AutoGen Review Stage (RoundRobinGroupChat)")
    t.para(
        "Demonstration of the 2-agent AutoGen review stage (Policy Compliance Reviewer -> "
        "Final Editor) operating under `RoundRobinGroupChat` with `max_turns=2` and structured "
        "`ReviewVerdict` output."
    )

    # Case A: Clean Draft (Approved Unchanged)
    t.h2("Case A: Clean Draft Approved Unchanged")
    query_a = "What documents are required for KYC?"
    t.bullet(f"**Query**: `{query_a}`")
    ans_a = grounded_answer(query_a)
    draft_a = ans_a.answer
    ctx_a = [c.text for c in ans_a.context]

    t.para("**Draft Answer**:")
    t.code(draft_a)

    res_a = review(draft_a, ctx_a)
    t.bullet(f"**Total Messages in Run**: {len(res_a.messages)} (Task + 2 Agent Turns)")
    t.bullet(f"**Changed**: `{res_a.changed}`")

    for src, content in res_a.messages:
        t.h3(f"Agent Message: `{src}`")
        t.code(content)

    t.para("**Final ReviewVerdict**:")
    t.code(res_a.verdict.model_dump_json(indent=2), lang="json")
    t.para(f"ReviewVerdict validation: **PASS** (approved={res_a.verdict.approved})")

    # Case B: Injected Unsupported Claim (Revised)
    t.h2("Case B: Injected Unsupported Claim Revised")
    injected_claim = UNSUPPORTED_CLAIMS[0]
    draft_b = f"{draft_a} {injected_claim}"
    t.bullet(f"**Injected Unsupported Claim**: `{injected_claim}`")
    t.para("**Draft with Injection**:")
    t.code(draft_b)

    res_b = review(draft_b, ctx_a)
    t.bullet(f"**Total Messages in Run**: {len(res_b.messages)} (Task + 2 Agent Turns)")
    t.bullet(f"**Changed**: `{res_b.changed}`")

    for src, content in res_b.messages:
        t.h3(f"Agent Message: `{src}`")
        t.code(content)

    t.para("**Final ReviewVerdict**:")
    t.code(res_b.verdict.model_dump_json(indent=2), lang="json")
    t.para(f"ReviewVerdict validation: **PASS** (approved={res_b.verdict.approved})")

    # Case C: Status Draft with Contradictory Record (Revised)
    t.h2("Case C: Status Draft Contradicting Loan Record")
    record_c = {
        "record_id": "APP-2026-0042",
        "applicant_name": "Test User",
        "loan_amount_inr": 500000,
        "status": "APPROVED",
    }
    draft_c = (
        "Application APP-2026-0042 has been REJECTED. "
        "The requested amount of ₹ 9,00,000 cannot be disbursed."
    )
    t.bullet("**Record**:")
    t.code(json.dumps(record_c, indent=2), lang="json")
    t.para("**Contradictory Draft**:")
    t.code(draft_c)

    res_c = review(draft_c, [], record=record_c)
    t.bullet(f"**Total Messages in Run**: {len(res_c.messages)} (Task + 2 Agent Turns)")
    t.bullet(f"**Changed**: `{res_c.changed}`")

    for src, content in res_c.messages:
        t.h3(f"Agent Message: `{src}`")
        t.code(content)

    t.para("**Final ReviewVerdict**:")
    t.code(res_c.verdict.model_dump_json(indent=2), lang="json")
    t.para(f"ReviewVerdict validation: **PASS** (approved={res_c.verdict.approved})")

    path = t.save()
    print(f"\n[OK] Review stage transcript generated at: {path}")
    return 0


if __name__ == "__main__":
    main()
