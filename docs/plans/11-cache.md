# Plan 11 — Response cache for grounded generation

## Goal
An in-memory cache keyed by normalised query text around the grounded-generation step,
so a repeated query skips retrieval + generation, with hit/miss counters and
before/after evidence (call counters and timing).

## Brief tasks
T16. Acceptance: "Response caching is demonstrated producing a real cache hit with
before/after evidence on a repeated query."

## Depends on
04 (`grounded_answer`). If plan 08 is done, also wire into `rag_tool.rag_lookup`
(one-line change); if not, plan 08 must call `cached_grounded_answer` — note in PROGRESS.

## Read first
`credobot/rag/generate.py`, `credobot/tools/rag_tool.py` (if present), `credobot/counters.py`.

## Files
```
+ credobot/cache.py
~ credobot/tools/rag_tool.py          # use cached_grounded_answer
+ tests/test_cache.py
+ transcripts/part4_cache.md          (generated)
```

## Code changes — `credobot/cache.py`
```python
def normalize_query(q: str) -> str:
    """NFKC → casefold → collapse whitespace → strip leading/trailing whitespace and
    trailing punctuation [?.!]. 'How is EMI  calculated?' == 'how is emi calculated'."""

class ResponseCache:
    def __init__(self, max_entries: int = 512, ttl_seconds: float | None = 3600): ...
    # OrderedDict LRU + per-entry timestamp; threading.Lock (API runs handlers in threads)
    def key(self, query: str, collection: str) -> str   # f"{collection}::{normalize_query(query)}"
    def get(self, key) -> GroundedAnswer | None          # counters.incr('cache.hit'/'cache.miss')
    def set(self, key, value) -> None
    def clear(self) -> None
    def stats(self) -> dict                              # hits, misses, size

RESPONSE_CACHE = ResponseCache()

def cached_grounded_answer(query: str, collection: str | None = None) -> tuple[GroundedAnswer, bool]:
    """Returns (answer, cache_hit). The key uses the *masked* query — callers pass the
    already-masked text (plan 14 guarantees this) so raw PII is never a cache key.
    Don't cache fallback (IDK) answers? → DO cache them: they're deterministic, and it
    saves a Chroma query. Never cache refusals from guardrails (those don't reach here)."""
```
`rag_tool.rag_lookup` switches to `cached_grounded_answer` and includes `"cache_hit"` in
its JSON. Expose `RESPONSE_CACHE.stats()` for the API `/health` (plan 15).

### Demo (`python -m credobot.cache` → `transcripts/part4_cache.md`)
1. `RESPONSE_CACHE.clear()`; `counters.reset()`.
2. Call 1: `"What is the penalty for prepaying a home loan?"` — record
   `time.perf_counter()` duration, counters `llm.generate`, `chroma.query`, `cache.miss`.
3. Call 2: `"  what is the PENALTY for prepaying a home loan "` — same metrics.
4. Table: call #, normalised key, cache_hit, duration ms, Δ`llm.generate`, Δ`chroma.query`.
   Expect call 2: hit, Δ = 0 for both, duration ≪ call 1.
5. Optional section: same pair through `run_crew` showing `rag_lookup` tool ran but
   `llm.generate` didn't increase on the second run.

## Tests — `tests/test_cache.py`
- `test_normalize_query_equivalences` (parametrized).
- `test_miss_then_hit` (isolated_env) — second call returns `cache_hit=True`, identical
  answer, `chroma.query` and `llm.generate` counters unchanged by the 2nd call.
- `test_different_collection_different_key`.
- `test_lru_eviction` — max_entries=2.
- `test_ttl_expiry` — monkeypatch `time.monotonic`.
- `test_thread_safety_smoke` — 8 threads × 50 get/set, no exceptions, size ≤ max.

## Steps
- [x] `cache.py` + tests
- [x] Wire into `rag_tool.py` (if present)
- [x] Demo + transcript
- [x] Verify; PROGRESS; commit

## Verify
1. `uv run python -m credobot.cache` → table shows call 2 is a hit with zero LLM/Chroma
   delta and lower latency.
2. `uv run pytest tests/test_cache.py -q` (+ `tests/test_crew.py` if 08 done) → pass.

## Record in DECISIONS.md
Nothing new.

## Pitfalls
- Cache key must be on masked text (see docstring) — never raw input.
- First call includes model warm-up; warm the embedder before timing (call `embed(["warmup"])`)
  so the timing comparison is fair, and say so in the transcript.

## Commit
`plan 11: normalised-query response cache for grounded generation`
