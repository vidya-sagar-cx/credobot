# Plan 14 — End-to-end pipeline

## Goal
One function, `pipeline.answer()`, that composes every stage in the correct order and is
the only entry point used by the API, the memory layer, the evaluation and the final
demos — so all of them exercise identical behaviour.

## Brief tasks
None new; integrates T8–T10, T14–T16 for T11–T13.

## Depends on
09, 10, 11, 12, 13

## Read first
`credobot/guardrails/*`, `credobot/governance/budget.py`, `credobot/cache.py`,
`credobot/memory.py`, `credobot/crew/crew.py`, `credobot/review/autogen_review.py`.

## Files
```
+ credobot/pipeline.py
~ credobot/memory.py               # set_turn_handler(pipeline turn)
~ credobot/crew/crew.py            # expose retrieved context from the crew run
+ tests/test_pipeline.py
+ transcripts/pipeline_e2e.md      (generated)
```

## Code changes — `credobot/pipeline.py`
Order (each stage records a `StageEvent(name, ms, detail)`):
```
1. budget      enforce_budget(raw_query)              → BudgetExceededError propagates (API → 413)
2. input_guard check_input(raw_query)                 → masked_query, events
               if injection → return refused PipelineResult (no crew, no LLM calls)
3. memory      resolve_followup(masked_query, history) → resolved_query
4. crew        run_crew(resolved_query)                → CrewRun (rag_lookup uses the cache)
5. output_guard check_grounded(policy part of answer, hits) → if not grounded:
               response.answer = REFUSAL_UNGROUNDED (keep status sentence if a record exists),
               response.grounded=False, events += ["groundedness_refused"]
6. review      review(draft=response.answer, context=[h.text…], record=response.record)
               → ReviewVerdict; response.answer = verdict.final_answer
               (skip review for refused answers — nothing to review; verdict =
               approved True, reason "refusal passthrough")
7. validate    CrewResponse.model_validate(response.model_dump()) (final schema check)
```
```python
@dataclass
class PipelineResult:
    trace_id: str
    query_masked: str
    resolved_query: str
    response: CrewResponse
    verdict: ReviewVerdict
    cache_hit: bool
    events: list[str]                 # guardrail + governance events
    stages: list[StageEvent]
    budget: BudgetEstimate
    counters_delta: dict[str, int]

def answer(query: str, session_id: str | None = None, trace_id: str | None = None) -> PipelineResult:
    """If session_id is given, route through memory.CONVERSATION so history is updated
    (history stores MASKED text only). Without session_id, run stateless."""
```
To give the output guard and reviewer the retrieved context, extend `CrewRun` (plan 08)
with `context: list[Hit]` parsed from the `rag_lookup` JSON (`"context"` field). If the
cache served it, the cached `GroundedAnswer.context` is used — same data.

`memory.set_turn_handler(...)` is called at import time of `pipeline` so
`memory.chat()` runs stages 3–7 (stages 1–2 happen before memory so raw PII never enters
history).

### Demo (`python -m credobot.pipeline` → `transcripts/pipeline_e2e.md`)
Five queries showing the stage table for each: policy, status (escalated), mixed with
PII, injection, out-of-scope. Columns: stage, ms, detail.

## Tests — `tests/test_pipeline.py` (isolated_env)
- `test_policy_query_full_path` — stages in exact order; verdict approved; response valid.
- `test_injection_short_circuits` — no `llm.*` or `tool.*` counters incremented.
- `test_pii_never_reaches_crew_or_history` — raw PAN/Aadhaar/account absent from
  `resolved_query`, from every message in the session history, and from `query_masked`.
- `test_budget_rejected_before_anything` — raises; all counters zero.
- `test_oos_refused_and_not_reviewed`.
- `test_second_identical_query_cache_hit` — `cache_hit True`, `llm.generate` delta 0.
- `test_session_followup_through_pipeline` — turn 2 resolves record id from turn 1.

## Steps
- [ ] Extend `CrewRun` with context
- [ ] `pipeline.py`
- [ ] Wire memory turn handler
- [ ] Demo + transcript; tests
- [ ] Run full suite `uv run pytest -q` (no regressions)
- [ ] PROGRESS; commit

## Verify
1. `uv run python -m credobot.pipeline` → 5 stage tables; injection row stops after
   input_guard; OOS refused.
2. `uv run pytest -q` → entire suite passes.

## Record in DECISIONS.md
Nothing new.

## Pitfalls
- Budget check must use the raw length (that's what costs tokens) but must not log raw text.
- Don't double-mask (masking is idempotent, but events would double-count) — mask once.

## Commit
`plan 14: end-to-end pipeline wiring guardrails, budget, memory, crew, review`
