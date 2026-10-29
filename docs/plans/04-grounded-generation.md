# Plan 04 — Retrieval, IDK-threshold calibration & grounded generation

## Goal
Top-k retrieval with cosine similarity from either collection, an empirically calibrated
"I don't know" threshold, and a grounded-generation function that answers only from
retrieved context (extractive under `MOCK_LLM`, prompt-constrained with a real LLM).

## Brief tasks
T4. Acceptance: "Grounded generation is demonstrated on ≥5 in-scope queries plus 1
out-of-scope query that correctly triggers the 'I don't know' fallback." Also the
README statement of measured values/threshold (values recorded here, README in 17).

## Depends on
03 (uses `index.get_collection`, `embeddings.embed`, `kb.split_sentences`)

## Read first
`credobot/rag/index.py`, `credobot/rag/embeddings.py`, `credobot/counters.py`.

## Files
```
+ credobot/rag/retrieve.py
+ credobot/rag/calibrate.py
+ credobot/rag/generate.py
+ credobot/rag/queries.py           # shared demo/eval query lists
~ credobot/config.py                # set IDK_THRESHOLD
+ tests/test_retrieve_generate.py
+ transcripts/part1_calibration.md  (generated)
+ transcripts/part1_grounded.md     (generated)
```

## Code changes

### `credobot/rag/queries.py`
```python
IN_SCOPE = [   # ≥5, each with hand-labelled relevant doc_ids (reused by plan 05)
    ("How is the EMI on my loan calculated?",                 {"emi_calculation"}),
    ("What documents are required to complete KYC?",          {"kyc_documents"}),
    ("Is there a penalty if I prepay my home loan early?",    {"prepayment_penalty"}),
    ("Who is eligible to open an NRI account?",               {"nri_accounts"}),
    ("What is the minimum balance I must keep in a savings account?", {"minimum_balance"}),
    ("What credit score do I need for a personal loan and what rate will I get?",
                                     {"loan_eligibility", "interest_rate_slabs"}),
]
OUT_OF_SCOPE = [
    "What is the capital of Australia?",
    "Give me a recipe for chocolate cake.",
    "Who won the 2018 football world cup?",
]
```

### `credobot/rag/retrieve.py`
```python
@dataclass
class Hit:
    chunk_id: str; doc_id: str; text: str; similarity: float  # = 1 - cosine distance

def retrieve(query: str, collection: str | None = None, k: int = config.TOP_K) -> list[Hit]:
    """collection defaults to config.DEPLOY_COLLECTION or 'kb_sentence' if None.
    ensure_index(); counters.incr('chroma.query'); query_embeddings=embed([query]);
    include=['documents','metadatas','distances']; sorted by similarity desc."""

def top1_similarity(hits) -> float  # 0.0 if no hits
```

### `credobot/rag/calibrate.py` (`python -m credobot.rag.calibrate`)
- For each query in `IN_SCOPE` (≥5) and `OUT_OF_SCOPE` (≥3), for BOTH collections,
  record top-1 similarity.
- Compute per collection: `min_in`, `max_out`; gap check `min_in > max_out` (if not,
  print a warning — fix KB wording or queries, do not fudge).
- Recommended threshold = `round((min_in + max_out) / 2, 2)`; if the two collections
  give different values, use the threshold that separates both (the midpoint of the
  overall `min_in` and overall `max_out`).
- Write `transcripts/part1_calibration.md` with a per-query table
  (query, in/out, sim_fixed, sim_sentence) and the derived threshold.
- Then **manually** set `IDK_THRESHOLD = <value>` in `config.py` (allow env override
  `IDK_THRESHOLD`) and record the measured values in DECISIONS.md.

### `credobot/rag/generate.py`
```python
IDK_MESSAGE = ("I don't know — the X Corp policy knowledge base doesn't cover that. "
               "Please contact lending operations.")

@dataclass
class GroundedAnswer:
    query: str; answer: str; grounded: bool; fallback: bool
    top_similarity: float; sources: list[str]; context: list[Hit]

def build_prompt(query, hits) -> str:
    """'Answer ONLY using the context below. If the context does not contain the answer,
    reply exactly: <IDK_MESSAGE>.' + numbered context blocks + question."""

def _mock_generate(query, hits, max_sentences=2) -> str:
    """Extractive: split every hit's text into sentences (kb.split_sentences), embed them,
    rank by cosine sim to the query embedding, return the top `max_sentences` joined in
    original order. Output is a verbatim subset of the context → grounded by construction."""

def grounded_answer(query: str, collection: str | None = None, k: int = config.TOP_K) -> GroundedAnswer:
    hits = retrieve(query, collection, k)
    if not hits or hits[0].similarity < config.IDK_THRESHOLD:
        return GroundedAnswer(..., answer=IDK_MESSAGE, grounded=False, fallback=True)
    counters.incr("llm.generate")
    text = _mock_generate(...) if config.MOCK_LLM else factory.get_text_llm()(build_prompt(...))
    return GroundedAnswer(..., sources=sorted({h.doc_id for h in hits}))
```
`factory.get_text_llm` comes from plan 07. If 07 isn't done yet, import it lazily inside
the real-LLM branch only (tests run mock, so they don't need it).

### Demo (`main()` in `generate.py`, `python -m credobot.rag.generate`)
For every `IN_SCOPE` query and `OUT_OF_SCOPE[0]`: print/write query, top-1 sim, sources,
answer, fallback flag → `transcripts/part1_grounded.md`. Run against the
`kb_sentence` collection and show the fixed collection's top-1 too.

## Tests — `tests/test_retrieve_generate.py` (use `isolated_env`)
- `test_retrieve_sorted_and_bounded` — k hits, similarities descending, in [-1, 1].
- `test_retrieve_counts_chroma_query` — `counters.get("chroma.query")` increments.
- `test_threshold_separates_clusters` — every IN_SCOPE top-1 ≥ IDK_THRESHOLD and every
  OUT_OF_SCOPE top-1 < IDK_THRESHOLD in both collections.
- `test_in_scope_answer_grounded` — for each IN_SCOPE query: `fallback is False` and
  every answer sentence appears verbatim in some retrieved hit text.
- `test_out_of_scope_fallback` — `answer == IDK_MESSAGE`, `fallback is True`,
  `llm.generate` counter not incremented.

## Steps
- [ ] `queries.py`, `retrieve.py`
- [ ] `calibrate.py`; run it; inspect clusters
- [ ] Set `IDK_THRESHOLD` in config from the measurement
- [ ] `generate.py` (+ demo main)
- [ ] Tests; Verify; DECISIONS; PROGRESS; commit

## Verify
1. `uv run python -m credobot.rag.calibrate` → table printed, `min_in > max_out` for both
   collections, recommended threshold shown.
2. `uv run python -m credobot.rag.generate` → 6 in-scope answers (no fallback) + 1 OOS
   answer equal to the IDK message.
3. `uv run pytest tests/test_retrieve_generate.py -q` → pass.

## Record in DECISIONS.md
`calibration_sims` (the full table or min_in/max_out per collection), `idk_threshold`, `top_k`.

## Pitfalls
- Don't pick 0.5/0.6/0.7 by habit — MiniLM similarities for short policy sentences can be
  in the 0.3–0.6 range; use what you measure.
- Chroma returns cosine *distance*; similarity = `1 - distance`.
- If an OOS query lands above an in-scope one, improve KB wording / query phrasing and
  re-measure; document it.

## Commit
`plan 04: retrieval, calibrated IDK threshold and grounded generation`
