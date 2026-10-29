# Plan 12 — Session memory (LangChain)

## Goal
Per-session, in-process conversation memory using `InMemoryChatMessageHistory` +
`RunnableWithMessageHistory`, wrapping the crew so follow-up questions resolve from
earlier turns; demonstrated by one multi-turn transcript and one separate fresh-session
transcript where state is absent.

## Brief tasks
T8. Acceptance: "Multi-turn memory is demonstrated, with a separate fresh-conversation
transcript showing it correctly absent."

## Depends on
08 (`run_crew`, `CrewResponse`)

## Read first
`credobot/crew/crew.py`; LangChain docs for `RunnableWithMessageHistory`
(langchain-core version in DECISIONS `pkg_versions`).

## Files
```
+ credobot/memory.py
+ tests/test_memory.py
+ transcripts/part2_memory_multiturn.md   (generated)
+ transcripts/part2_memory_fresh.md       (generated)
```

## Code changes — `credobot/memory.py`
```python
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import HumanMessage, AIMessage

_STORE: dict[str, InMemoryChatMessageHistory] = {}
_LOCK = threading.Lock()

def get_session_history(session_id: str) -> InMemoryChatMessageHistory   # create on miss
def reset_session(session_id: str) -> None
def list_sessions() -> list[str]

@dataclass
class ResolvedQuery:
    original: str; resolved: str; used_memory: bool; note: str

def resolve_followup(query: str, history: list[BaseMessage]) -> ResolvedQuery:
    """Deterministic coreference for MOCK mode (also used with real LLM — cheap & testable):
    - If query has no LA-#### but contains a pronoun/reference ('it', 'its', 'that
      application', 'my application', 'the same loan', 'that one') → append the most recent
      record id found in history (search AIMessage additional_kwargs['record_id'] then text).
    - If query asks 'what did I (first|last) ask' → answer from HumanMessages directly.
    - If the query is a bare policy follow-up ('and for home loans?', 'what about
      prepayment?') → prefix the previous user topic.
    note explains what was resolved; used in transcripts."""

def _turn(inputs: dict) -> AIMessage:
    """inputs: {'query': str, 'history': list[BaseMessage]}.
    resolved = resolve_followup(...); if a meta question → answer directly from history;
    else run = run_crew(resolved.resolved, history_note=...);
    return AIMessage(content=run.response.answer,
                     additional_kwargs={'record_id': ..., 'response': run.response.model_dump(),
                                        'resolved_query': resolved.resolved})"""

CONVERSATION = RunnableWithMessageHistory(
    RunnableLambda(_turn), get_session_history,
    input_messages_key="query", history_messages_key="history")

def chat(query: str, session_id: str) -> tuple[CrewResponse, ResolvedQuery]:
    msg = CONVERSATION.invoke({"query": query},
                              config={"configurable": {"session_id": session_id}})
    return CrewResponse.model_validate(msg.additional_kwargs["response"]), ...
```
Plan 14's pipeline replaces the inner `run_crew` call with the guarded pipeline; keep
`_turn` delegating to a single injectable callable (`set_turn_handler(fn)`) so that
swap needs no changes here.

### Demo (`python -m credobot.memory`)
- `part2_memory_multiturn.md`, session `"member-A"`:
  1. "What is the status of application LA-10xx?" → status answer (lookup tool ran).
  2. "What is its loan amount and is it escalated?" → resolved to LA-10xx (shown), correct
     amount from dataset.
  3. "What did I ask first?" → returns turn-1 text from memory.
  Show history length after each turn (2, 4, 6 messages).
- `part2_memory_fresh.md`, NEW session `"member-B"` (and also `reset_session("member-A")`
  then re-ask):
  1. "What is its loan amount and is it escalated?" → no record id resolved;
     answer asks for an application id (intent `unknown`/no record); history length before = 0.
  2. "What did I ask first?" → "This is the start of our conversation."
Print the `LangChainDeprecationWarning` if it appears — it's expected (note in transcript).

## Tests — `tests/test_memory.py` (isolated_env)
- `test_history_grows_per_turn`.
- `test_followup_resolves_record_id_within_session`.
- `test_fresh_session_has_no_state` — new session id → `used_memory False`, no record.
- `test_sessions_isolated` — A's record never resolves in B.
- `test_reset_session_clears`.
- `test_what_did_i_ask_first`.
- `test_resolve_followup_unit` — pure function with handcrafted histories.

## Steps
- [ ] `memory.py` (`resolve_followup` first, with unit tests)
- [ ] Runnable wiring + `chat()`
- [ ] Demo → 2 transcripts
- [ ] Verify; PROGRESS; commit

## Verify
1. `uv run python -m credobot.memory` → two transcript files; multi-turn shows resolution;
   fresh shows absence.
2. `uv run pytest tests/test_memory.py -q` → pass.

## Record in DECISIONS.md
Nothing new.

## Pitfalls
- `RunnableWithMessageHistory` emits `LangChainDeprecationWarning` — expected; don't
  suppress globally (brief says it needn't be silenced).
- The runnable must return a `BaseMessage` (or str) so history is appended correctly.
- Memory is process-local; the API (plan 15) shares `_STORE` across requests via session_id.

## Commit
`plan 12: LangChain session memory with follow-up resolution and transcripts`
