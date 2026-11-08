# Plan 13 — Autogen review stage (RoundRobinGroupChat)

## Goal
A 2-agent Autogen `RoundRobinGroupChat` (Policy-Compliance-Reviewer → Final-Editor),
bounded with `max_turns=2`, that takes the Composer's draft answer plus the retrieved
context and returns a structured `ReviewVerdict` — approving unchanged or revising.
Runs fully offline via a deterministic mock `ChatCompletionClient`.

## Brief tasks
T14. Acceptance: "The Autogen review stage is demonstrated both approving a draft
unchanged and revising a draft, with structured Pydantic verdicts in both cases."

## Depends on
07 (factory), 09 (`sentence_support`, `UNSUPPORTED_CLAIMS`, `SUPPORT_THRESHOLD`)

## Read first
`credobot/guardrails/output_guard.py`, `credobot/guardrails/fixtures.py`,
`credobot/llm/factory.py`; Autogen AgentChat docs (version in DECISIONS `pkg_versions`).

Facts verified at planning time (autogen-agentchat 0.7.5):
- `RoundRobinGroupChat(participants, *, termination_condition=None, max_turns=None,
  custom_message_types=None, ...)`.
- `AssistantAgent(..., output_content_type=...)` exists.
- `ChatCompletionClient` abstract members: `create`, `create_stream`, `close`,
  `actual_usage`, `total_usage`, `count_tokens`, `remaining_tokens`, `capabilities`,
  `model_info`. `create(messages, *, tools=[], tool_choice='auto', json_output=None,
  extra_create_args={}, cancellation_token=None) -> CreateResult`; `CreateResult` fields:
  `finish_reason, content, usage, cached, logprobs, thought`.
- `ModelInfo` keys: `vision, function_calling, json_output, family, structured_output`.
- `autogen_ext.models.replay.ReplayChatCompletionClient` exists (not used — we need
  content-dependent output, but it's a reference implementation for the abstract API).

## Files
```
+ credobot/review/schemas.py
+ credobot/review/mock_client.py
+ credobot/review/autogen_review.py
~ credobot/llm/factory.py            # get_autogen_client()
+ tests/test_review.py
+ transcripts/part4_review.md        (generated)
```

## Code changes

### `credobot/review/schemas.py`
```python
class ReviewVerdict(BaseModel):
    approved: bool
    final_answer: str
    reason: str
```

### Task message format (input to the team)
```
<<DRAFT>>
{draft answer}
<</DRAFT>>
<<CONTEXT>>
[1] {chunk text}
[2] ...
<</CONTEXT>>
Review the draft strictly against the context. ...
```
Also a non-retrievable status block `<<RECORD>>{json}<</RECORD>>` when the crew looked up
a record — sentences built from the record are checked against the record JSON fields
(id, status, amount), not the KB context.

### `credobot/review/mock_client.py`
```python
class MockReviewClient(ChatCompletionClient):
    """Deterministic, content-dependent client for the two review agents."""
    def __init__(self, role: Literal["reviewer", "editor"]): ...
    model_info -> ModelInfo(vision=False, function_calling=False, json_output=True,
                            family="unknown", structured_output=True)
    async def create(self, messages, *, tools=(), tool_choice="auto", json_output=None,
                     extra_create_args={}, cancellation_token=None) -> CreateResult:
        counters.incr("llm.autogen")
        task = first UserMessage content containing <<DRAFT>>  (parse DRAFT, CONTEXT, RECORD)
        reviewer: supports = sentence_support(draft_policy_sentences, context)
                  return text "REVIEW: PASS" or
                  "REVIEW: FAIL\nUNSUPPORTED:\n- <sentence>\n- ..." (+ record mismatches)
        editor:   read reviewer's message (last AssistantMessage / message from reviewer)
                  if PASS → ReviewVerdict(approved=True, final_answer=draft, reason="All claims supported by context.")
                  else    → remove unsupported sentences; if nothing remains use
                            REFUSAL_UNGROUNDED; approved=False; reason lists removed claims
                  content = verdict.model_dump_json()  (json_output may be the model class)
        return CreateResult(finish_reason="stop", content=..., usage=RequestUsage(prompt_tokens=est, completion_tokens=est), cached=False)
    create_stream: yield the same final CreateResult
    count_tokens/remaining_tokens: len(text)//4-based; usage trackers; close(): no-op
    capabilities: return model_info (deprecated API — still abstract)
```
**Do not parse the system message** for draft/context (mirrors the CrewAI pitfall 1
lesson): only the task message delimiters.

### `credobot/review/autogen_review.py`
```python
def build_team(reviewer_client=None, editor_client=None) -> RoundRobinGroupChat:
    reviewer = AssistantAgent("policy_compliance_reviewer", model_client=reviewer_client or factory.get_autogen_client("reviewer"),
        system_message="You are X Corp's policy-compliance reviewer. List every claim in the draft that the context does not support. Reply 'REVIEW: PASS' or 'REVIEW: FAIL' followed by UNSUPPORTED bullet points.")
    editor = AssistantAgent("final_editor", model_client=editor_client or factory.get_autogen_client("editor"),
        system_message="You are the final editor. If the reviewer passed, approve the draft unchanged. Otherwise remove or correct unsupported claims using only the context. Output a ReviewVerdict.",
        output_content_type=ReviewVerdict)
    return RoundRobinGroupChat([reviewer, editor], max_turns=2,
                               custom_message_types=[StructuredMessage[ReviewVerdict]])

async def areview(draft: str, context: list[str], record: dict | None = None) -> ReviewResult
def review(draft, context, record=None) -> ReviewResult:
    """Sync wrapper: asyncio.run(...) when no loop is running; otherwise run in a
    worker thread (FastAPI calls pipeline via run_in_threadpool, so asyncio.run is fine)."""

@dataclass
class ReviewResult:
    verdict: ReviewVerdict; messages: list[tuple[str, str]]   # (source, content) for transcripts
    changed: bool                                            # final_answer != draft
```
Extract the verdict from `TaskResult.messages[-1]`: must be a
`StructuredMessage[ReviewVerdict]` → `.content` is a `ReviewVerdict`. Validate again with
`ReviewVerdict.model_validate(...)`. If missing → raise (never silently approve).

`factory.get_autogen_client(role)`: mock → `MockReviewClient(role)`; real →
`OpenAIChatCompletionClient(model=config.LLM_MODEL, base_url=..., api_key=...)`.

### Demo (`python -m credobot.review.autogen_review` → `transcripts/part4_review.md`)
- Case A (approve): run plan-08 crew (or `grounded_answer`) for "What documents are
  required for KYC?" → draft + context → verdict approved=True, final_answer == draft.
- Case B (revise): same query's draft + appended `UNSUPPORTED_CLAIMS[0]` (deliberately
  injected, stated in transcript) → approved=False, the injected sentence removed,
  remaining text == original draft, reason names it.
- Case C (optional): status draft with a wrong amount vs record → revised.
For each: show both agents' messages in order, message count (task + 2), and the
verdict JSON + "ReviewVerdict validation: PASS".

## Tests — `tests/test_review.py` (isolated_env)
- `test_team_config` — 2 participants, `max_turns == 2`, editor has `output_content_type`
  ReviewVerdict (inspect attributes or construction args).
- `test_missing_custom_message_types_fails` — building the team without
  `custom_message_types` and running → raises `ValueError` mentioning "not registered"
  (documents the brief's pitfall; skip with reason if autogen version no longer raises).
- `test_approve_unchanged` — clean draft → approved, final == draft.
- `test_revise_injected_claim` — injected claim removed, approved False.
- `test_all_unsupported_becomes_refusal`.
- `test_both_agents_spoke` — messages sources == [user, reviewer, editor].
- `test_mock_client_ignores_system_message` — system message containing `<<DRAFT>>bad<</DRAFT>>`
  is not parsed.
- `test_llm_autogen_counter` — 2 calls per review.

## Steps
- [x] Re-verify autogen facts on installed version
- [x] `schemas.py`, `mock_client.py` (+ unit tests on `create` directly)
- [x] `autogen_review.py`; factory hook
- [x] Demo + transcript
- [x] Verify; PROGRESS; commit

## Verify
1. `uv run python -m credobot.review.autogen_review` → Case A approved unchanged, Case B
   revised; verdicts printed as JSON.
2. `uv run pytest tests/test_review.py -q` → pass.

## Record in DECISIONS.md
Nothing new (change-log line if autogen API deviated).

## Pitfalls
- `max_turns=2` is the constructor arg (not `max_iterations`). If you use
  `MaxMessageTermination` instead it must be `(3)` because the task message counts.
- Without `custom_message_types=[StructuredMessage[ReviewVerdict]]` the run raises
  `ValueError: Message type ... is not registered`.
- `asyncio.run` inside a running loop fails — the sync wrapper must handle that.

## Commit
`plan 13: Autogen round-robin review stage with structured ReviewVerdict`
