# Plan 05 — Chunking strategy evaluation (document-level P/R)

## Goal
Precision and recall at the document level for both collections on the same query set
used in plan 04, with visible per-query arithmetic, macro averages, and a numbers-cited
recommendation that sets the deployed collection.

## Brief tasks
T5. Acceptance: "Precision/recall are computed for BOTH collections on the same ≥5
queries with visible per-query arithmetic, and a numbers-cited recommendation is given."

## Depends on
04 (`retrieve`, `queries.IN_SCOPE`)

## Read first
`credobot/rag/queries.py`, `credobot/rag/retrieve.py`, DECISIONS `top_k`.

## Files
```
+ credobot/rag/eval_chunking.py
~ credobot/config.py                    # DEPLOY_COLLECTION
+ tests/test_eval_chunking.py
+ transcripts/part1_chunking_eval.md    (generated)
```

## Code changes — `credobot/rag/eval_chunking.py`
```python
@dataclass
class PRRow:
    query: str
    collection: str
    retrieved_chunks: list[str]   # chunk ids in rank order
    retrieved_docs: list[str]     # mapped to doc_id, de-duplicated, order preserved
    relevant_docs: set[str]
    hits: int                     # |relevant ∩ retrieved_docs|
    precision: float              # hits / len(retrieved_docs)   (0 if empty)
    recall: float                 # hits / len(relevant_docs)
    def arithmetic(self) -> str:
        return f"P = {self.hits}/{len(self.retrieved_docs)} = {self.precision:.2f}; " \
               f"R = {self.hits}/{len(self.relevant_docs)} = {self.recall:.2f}"

def score_query(query, relevant, collection, k=config.TOP_K) -> PRRow
def evaluate(queries=IN_SCOPE, collections=("kb_fixed", "kb_sentence"), k=config.TOP_K)
    -> dict[str, list[PRRow]]
def macro(rows) -> tuple[float, float]           # mean P, mean R
def recommend(results) -> tuple[str, str]:
    """Pick higher macro F1 (2PR/(P+R)); tie → higher recall; tie → 'kb_sentence'
    (smaller, self-contained chunks are easier to verify for groundedness).
    Return (collection_name, 2–3 sentence paragraph quoting both sets of numbers)."""
def main()   # python -m credobot.rag.eval_chunking
```
Transcript layout (`part1_chunking_eval.md`), one section per collection:

| # | Query | Retrieved chunks → docs (dedup) | Relevant | Hits | Precision | Recall |
|---|---|---|---|---|---|---|
| 1 | How is the EMI… | s:emi:000, s:emi:001, s:int:002 → emi_calculation, interest_rate_slabs | emi_calculation | 1 | 1/2 = 0.50 | 1/1 = 1.00 |

then a summary table (collection, macro P, macro R, F1) and the recommendation paragraph.

After running: set `DEPLOY_COLLECTION = "<winner>"` in `config.py` (env override
`DEPLOY_COLLECTION`), and paste the paragraph into DECISIONS.md.

## Tests — `tests/test_eval_chunking.py`
- `test_pr_arithmetic_unit` — construct a PRRow by hand-calling `score_query` logic on
  a fake retrieve (monkeypatch `retrieve` to return chunks from docs [a, a, b]) with
  relevant {a, c} → retrieved_docs [a, b], hits 1, P 0.5, R 0.5; `arithmetic()` string
  contains `1/2`.
- `test_dedup_before_scoring` — duplicate doc chunks counted once.
- `test_evaluate_both_collections` (isolated_env) — results have both keys, each with
  `len(IN_SCOPE)` rows, all values in [0, 1].
- `test_recommend_tiebreak` — synthetic equal results → `kb_sentence`.

## Steps
- [ ] Implement `eval_chunking.py`
- [ ] Unit tests with monkeypatched retrieve
- [ ] Run the module; read numbers; set `DEPLOY_COLLECTION`
- [ ] Verify; DECISIONS; PROGRESS; commit

## Verify
1. `uv run python -m credobot.rag.eval_chunking` → two per-query tables with fractions,
   macro summary, recommendation naming one collection and citing both sets of numbers.
2. `uv run python -c "from credobot import config; print(config.DEPLOY_COLLECTION)"` → winner.
3. `uv run pytest tests/test_eval_chunking.py -q` → pass.

## Record in DECISIONS.md
`chunking_pr_results` (macro P/R/F1 per collection + recommendation paragraph),
`deploy_collection`.

## Pitfalls
- Precision is over *deduplicated documents*, not chunks — 3 chunks from one doc = 1 doc.
- Use exactly the same queries as plan 04 (import `IN_SCOPE`; don't copy them).

## Commit
`plan 05: document-level precision/recall for both chunking strategies`
