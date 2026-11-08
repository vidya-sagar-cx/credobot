"""In-process multi-turn conversation memory with deterministic coreference resolution."""
from dataclasses import dataclass
import re
import threading
from typing import Any, Callable

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory

from credobot.crew.schemas import CrewResponse
from credobot.tools.loan_status import RECORD_ID_RE

_STORE: dict[str, InMemoryChatMessageHistory] = {}
_LOCK = threading.Lock()
_TURN_HANDLER: Callable[..., Any] | None = None

PRONOUN_PATTERN = re.compile(
    r"\b(it|its|that application|my application|the same loan|that one|this loan|this application|the loan|the application|my loan)\b",
    re.IGNORECASE,
)
META_FIRST_PATTERN = re.compile(r"\bwhat did i first ask\b", re.IGNORECASE)
META_LAST_PATTERN = re.compile(r"\bwhat did i last ask\b", re.IGNORECASE)
BARE_FOLLOWUP_PATTERN = re.compile(r"^(and\b|what about\b|how about\b)", re.IGNORECASE)


@dataclass
class ResolvedQuery:
    original: str
    resolved: str
    used_memory: bool
    note: str


def set_turn_handler(fn: Callable[..., Any] | None) -> None:
    """Inject alternative execution handler (e.g. Plan 14 unified pipeline)."""
    global _TURN_HANDLER
    _TURN_HANDLER = fn


def _get_turn_handler() -> Callable[..., Any]:
    if _TURN_HANDLER is not None:
        return _TURN_HANDLER
    from credobot.crew.crew import run_crew

    return run_crew


def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    """Thread-safe getter creating an InMemoryChatMessageHistory on miss."""
    with _LOCK:
        if session_id not in _STORE:
            _STORE[session_id] = InMemoryChatMessageHistory()
        return _STORE[session_id]


def reset_session(session_id: str) -> None:
    """Thread-safe reset clearing session history."""
    with _LOCK:
        if session_id in _STORE:
            _STORE[session_id].clear()
            del _STORE[session_id]


def list_sessions() -> list[str]:
    """Return all active session IDs."""
    with _LOCK:
        return list(_STORE.keys())


def clear_all_sessions() -> None:
    """Clear all sessions (used in test teardown)."""
    with _LOCK:
        _STORE.clear()


def resolve_followup(query: str, history: list[BaseMessage]) -> ResolvedQuery:
    """Deterministic coreference resolution over chat history.

    - If query has no LA-#### but contains a pronoun/reference -> search history backwards for record_id.
    - If query asks 'what did I first/last ask' -> answer from HumanMessages directly.
    - If bare policy follow-up -> append previous question topic.
    """
    # 1. Meta question check
    if META_FIRST_PATTERN.search(query):
        human_msgs = [m for m in history if isinstance(m, HumanMessage) or getattr(m, "type", "") == "human"]
        if human_msgs:
            ans = f'You first asked: "{human_msgs[0].content}"'
        else:
            ans = "This is the start of our conversation — you haven't asked any previous questions."
        return ResolvedQuery(
            original=query,
            resolved=ans,
            used_memory=True,
            note="Answered meta question directly from user conversation history.",
        )

    if META_LAST_PATTERN.search(query):
        human_msgs = [m for m in history if isinstance(m, HumanMessage) or getattr(m, "type", "") == "human"]
        if human_msgs:
            ans = f'You last asked: "{human_msgs[-1].content}"'
        else:
            ans = "This is the start of our conversation — you haven't asked any previous questions."
        return ResolvedQuery(
            original=query,
            resolved=ans,
            used_memory=True,
            note="Answered meta question directly from user conversation history.",
        )

    # 2. Pronoun / Reference resolution to loan application record
    has_explicit_id = bool(RECORD_ID_RE.search(query))
    if not has_explicit_id and PRONOUN_PATTERN.search(query):
        # Search history in reverse for the most recent record_id
        found_id: str | None = None
        for m in reversed(history):
            if isinstance(m, AIMessage) and "record_id" in m.additional_kwargs:
                rec = m.additional_kwargs.get("record_id")
                if rec:
                    found_id = str(rec)
                    break
            match = RECORD_ID_RE.search(m.content)
            if match:
                found_id = match.group(0).upper()
                break

        if found_id:
            resolved_text = f"What is the status of application {found_id}? {query}"
            return ResolvedQuery(
                original=query,
                resolved=resolved_text,
                used_memory=True,
                note=f"Resolved pronoun reference to application {found_id} from previous turn.",
            )
        else:
            return ResolvedQuery(
                original=query,
                resolved=query,
                used_memory=False,
                note="Pronoun used but no previous loan application ID found in session history.",
            )

    # 3. Bare policy follow-ups
    if BARE_FOLLOWUP_PATTERN.search(query.strip()):
        human_msgs = [m for m in history if isinstance(m, HumanMessage) or getattr(m, "type", "") == "human"]
        if human_msgs:
            prev = human_msgs[-1].content
            resolved_text = f"{query} [Previous query context: {prev}]"
            return ResolvedQuery(
                original=query,
                resolved=resolved_text,
                used_memory=True,
                note=f"Attached context from previous query: '{prev}'.",
            )

    # 4. Self-contained query
    return ResolvedQuery(
        original=query,
        resolved=query,
        used_memory=False,
        note="Query is self-contained.",
    )


def _turn(inputs: dict[str, Any]) -> AIMessage:
    """Execute single conversational turn within LangChain runnable pipeline."""
    query = str(inputs.get("query", ""))
    history = inputs.get("history", [])
    resolved = resolve_followup(query, history)

    # If resolved as meta response
    if resolved.note.startswith("Answered meta question"):
        resp = CrewResponse(
            answer=resolved.resolved,
            intent="policy",
            sources=[],
            record=None,
            escalate=False,
            grounded=True,
            top_similarity=None,
            guardrail_events=[],
        )
        return AIMessage(
            content=resolved.resolved,
            additional_kwargs={
                "record_id": None,
                "response": resp.model_dump(),
                "resolved_obj": {
                    "original": resolved.original,
                    "resolved": resolved.resolved,
                    "used_memory": resolved.used_memory,
                    "note": resolved.note,
                },
            },
        )

    # If pronoun used without any record context in history
    if resolved.note.startswith("Pronoun used but no previous"):
        ans_text = (
            "Please provide your loan application ID (e.g. LA-1001) so I can look up its status and loan details."
        )
        resp = CrewResponse(
            answer=ans_text,
            intent="unknown",
            sources=[],
            record=None,
            escalate=False,
            grounded=False,
            top_similarity=None,
            guardrail_events=[],
        )
        return AIMessage(
            content=ans_text,
            additional_kwargs={
                "record_id": None,
                "response": resp.model_dump(),
                "resolved_obj": {
                    "original": resolved.original,
                    "resolved": resolved.resolved,
                    "used_memory": resolved.used_memory,
                    "note": resolved.note,
                },
            },
        )

    handler = _get_turn_handler()
    history_note = (
        f"\n<<HISTORY_NOTE>>{resolved.note}<</HISTORY_NOTE>>"
        if resolved.used_memory
        else ""
    )
    run = handler(resolved.resolved, history_note=history_note)
    resp = run.response
    rec_id = resp.record.record_id if resp.record else None

    return AIMessage(
        content=resp.answer,
        additional_kwargs={
            "record_id": rec_id,
            "response": resp.model_dump(),
            "resolved_obj": {
                "original": resolved.original,
                "resolved": resolved.resolved,
                "used_memory": resolved.used_memory,
                "note": resolved.note,
            },
        },
    )


CONVERSATION = RunnableWithMessageHistory(
    RunnableLambda(_turn),
    get_session_history,
    input_messages_key="query",
    history_messages_key="history",
)


def chat(query: str, session_id: str) -> tuple[CrewResponse, ResolvedQuery]:
    """Execute conversational query with per-session LangChain memory."""
    msg = CONVERSATION.invoke(
        {"query": query},
        config={"configurable": {"session_id": session_id}},
    )
    resp_dict = msg.additional_kwargs.get("response", {})
    res_info = msg.additional_kwargs.get("resolved_obj", {})
    resolved = ResolvedQuery(
        original=res_info.get("original", query),
        resolved=res_info.get("resolved", query),
        used_memory=res_info.get("used_memory", False),
        note=res_info.get("note", ""),
    )
    return CrewResponse.model_validate(resp_dict), resolved


def main() -> int:
    """Run demonstration generating multi-turn and fresh-session memory transcripts."""
    from credobot.demos.transcript import Transcript

    print("=" * 70)
    print("CREDOBOT SESSION MEMORY DEMONSTRATION")
    print("=" * 70)

    clear_all_sessions()

    # -------------------------------------------------------------
    # Transcript 1: Multi-turn session "member-A"
    # -------------------------------------------------------------
    sid_a = "member-A"
    t_multi = Transcript("part2_memory_multiturn", "Part 2 — Multi-Turn Session Memory")
    t_multi.h2("Multi-Turn Conversation Flow (Session: member-A)")
    t_multi.para(
        "Demonstrates LangChain in-process session memory with deterministic coreference resolution. "
        "Pronouns in Turn 2 ('its', 'it') resolve to the application ID introduced in Turn 1, "
        "and Turn 3 inspects conversational message history."
    )

    queries_a = [
        "What is the status of application LA-1007?",
        "What is its loan amount and is it escalated?",
        "What did I first ask?",
    ]

    for turn_idx, q in enumerate(queries_a, 1):
        hist_before = len(get_session_history(sid_a).messages)
        resp, res = chat(q, sid_a)
        hist_after = len(get_session_history(sid_a).messages)

        print(f"\n[Session {sid_a} - Turn {turn_idx}]")
        print(f"  User: '{q}'")
        print(f"  Resolved: '{res.resolved}'")
        print(f"  Used Memory: {res.used_memory} | Note: {res.note}")
        print(f"  History Messages: {hist_before} -> {hist_after}")
        print(f"  Answer: {resp.answer[:120]}...")

        t_multi.h3(f"Turn {turn_idx}: \"{q}\"")
        t_multi.bullet(f"**Resolved Query:** `{res.resolved}`")
        t_multi.bullet(f"**Coreference Resolution Note:** {res.note}")
        t_multi.bullet(f"**Used Memory:** `{res.used_memory}`")
        t_multi.bullet(f"**Session History Length:** {hist_before} messages -> {hist_after} messages")
        t_multi.bullet(f"**Intent:** `{resp.intent}`")
        if resp.record:
            t_multi.bullet(
                f"**Record Bound:** `{resp.record.record_id}` | "
                f"₹{resp.record.loan_amount_inr:,} | Status: `{resp.record.status}` | Escalate: `{resp.record.escalate}`"
            )
        t_multi.para(f"**Assistant Response:**\n> {resp.answer}")

    saved_multi = t_multi.save()
    print(f"\nMulti-turn transcript written to: {saved_multi}")

    # -------------------------------------------------------------
    # Transcript 2: Fresh session "member-B" (Absence of State)
    # -------------------------------------------------------------
    sid_b = "member-B"
    t_fresh = Transcript("part2_memory_fresh", "Part 2 — Fresh Session Memory Absence")
    t_fresh.h2("Fresh Conversation Flow (Session: member-B)")
    t_fresh.para(
        "Demonstrates complete session isolation and absence of carryover state. "
        "Asking the exact same follow-up in a fresh session confirms memory is strictly isolated "
        "and ungrounded pronouns cannot access other sessions' state."
    )

    queries_b = [
        "What is its loan amount and is it escalated?",
        "What did I first ask?",
    ]

    for turn_idx, q in enumerate(queries_b, 1):
        hist_before = len(get_session_history(sid_b).messages)
        resp, res = chat(q, sid_b)
        hist_after = len(get_session_history(sid_b).messages)

        print(f"\n[Session {sid_b} - Turn {turn_idx}]")
        print(f"  User: '{q}'")
        print(f"  Resolved: '{res.resolved}'")
        print(f"  Used Memory: {res.used_memory} | Note: {res.note}")
        print(f"  History Messages: {hist_before} -> {hist_after}")
        print(f"  Answer: {resp.answer[:120]}...")

        t_fresh.h3(f"Turn {turn_idx}: \"{q}\"")
        t_fresh.bullet(f"**Resolved Query:** `{res.resolved}`")
        t_fresh.bullet(f"**Coreference Resolution Note:** {res.note}")
        t_fresh.bullet(f"**Used Memory:** `{res.used_memory}`")
        t_fresh.bullet(f"**Session History Length:** {hist_before} messages -> {hist_after} messages")
        t_fresh.bullet(f"**Intent:** `{resp.intent}`")
        t_fresh.bullet(f"**Record Present:** `{'Yes' if resp.record else 'None (Correctly Absent)'}`")
        t_fresh.para(f"**Assistant Response:**\n> {resp.answer}")

    saved_fresh = t_fresh.save()
    print(f"Fresh session transcript written to: {saved_fresh}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
