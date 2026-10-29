# Plan 01 — Loan-application dataset generator

## Goal
`dataset.py` at repo root deterministically generates ≥40 fabricated loan applications,
validates every structural threshold from the brief, and prints the required report.

## Brief tasks
T1. Acceptance: "`dataset.py` generates ≥40 loan applications meeting every stated
structural threshold … with your design choices stated in README.md" (README part is
plan 17; this plan records the choices in DECISIONS.md).

## Depends on
00

## Read first
`docs/BRIEF.md` Part 1 Task 1; `credobot/config.py`.

## Files
```
+ dataset.py
+ tests/test_dataset.py
+ transcripts/part1_dataset.md   (generated)
```

## Code changes — `dataset.py`
Pure stdlib (`random`, `collections`, `dataclasses`/`TypedDict`). No credobot imports
except optionally `Transcript` inside `main()`.

```python
SEED = 2026                       # change seed/weights if validation fails; never hand-edit records
N_RECORDS = 60
CATEGORIES = ["Personal Loan", "Home Loan", "Auto Loan", "Education Loan", "Business Loan"]
STATUSES = ["Submitted", "Under Review", "Approved", "Rejected", "Disbursed"]
CATEGORY_WEIGHTS = [0.25, 0.20, 0.20, 0.15, 0.20]
STATUS_WEIGHTS   = [0.20, 0.25, 0.20, 0.15, 0.20]
FRAUD_PROBABILITY = 0.18
# INR ranges per category (min, max), rounded to the nearest ₹1,000.
AMOUNT_RANGES_INR = {
    "Personal Loan":  (50_000,     2_500_000),
    "Home Loan":      (1_000_000, 15_000_000),
    "Auto Loan":      (200_000,    3_000_000),
    "Education Loan": (100_000,    4_000_000),
    "Business Loan":  (500_000,   20_000_000),
}
AMOUNT_RATIONALE = ("Ranges mirror typical Indian retail-bank product limits: unsecured "
    "personal loans up to ₹25 lakh, home loans ₹10 lakh–₹1.5 crore, vehicle loans up to "
    "₹30 lakh, education up to ₹40 lakh and MSME business loans up to ₹2 crore.")

class LoanApplication(TypedDict):
    record_id: str                 # "LA-1001" … sequential
    category: str
    status: str
    loan_amount_inr: int
    days_since_created: int        # 0..30 inclusive
    flagged_for_fraud_review: bool

def generate(seed: int = SEED, n: int = N_RECORDS) -> list[LoanApplication]:
    rng = random.Random(seed)      # local RNG — never the global random module
    for i in range(n):
        category = rng.choices(CATEGORIES, CATEGORY_WEIGHTS)[0]
        status   = rng.choices(STATUSES, STATUS_WEIGHTS)[0]
        lo, hi   = AMOUNT_RANGES_INR[category]
        amount   = round(rng.randint(lo, hi), -3)
        days     = rng.randint(0, 30)
        fraud    = rng.random() < FRAUD_PROBABILITY
        ...

def stats(records) -> dict:   # {"n", "by_category": {...}, "by_status": {...}, "fraud_pct": float}

def validate(records) -> list[str]:
    """Return list of violated rules (empty == valid). Rules:
    n >= 40; every given category count >= 3; every given status count >= 1;
    10.0 <= fraud_pct <= 30.0; record_ids unique; 0 <= days <= 30;
    amount within its category range."""

LOAN_APPLICATIONS: list[LoanApplication] = generate()
RECORDS_BY_ID = {r["record_id"]: r for r in LOAN_APPLICATIONS}

def main() -> int:
    # print seed, weights, ranges, rationale, counts per category/status, fraud %
    # print "VALID" or each violation; write transcripts/part1_dataset.md; return exit code
if __name__ == "__main__":
    raise SystemExit(main())
```
Iteration rule: run `main()`. If `validate()` reports a violation, change `SEED` (or
weights) and rerun. Record how many seeds you tried in DECISIONS.md notes. Do NOT edit
records or post-filter them.

Transcript (`part1_dataset.md`): design-choices table (seed, n, weights, ranges,
rationale, fraud p), category-count table, status-count table, fraud % line, validation
result, and the first 10 records as a table.

## Tests — `tests/test_dataset.py`
- `test_deterministic` — `generate(SEED) == generate(SEED)`; a different seed differs.
- `test_min_records` — `len(LOAN_APPLICATIONS) >= 40`.
- `test_category_coverage` — each of the 5 given categories has ≥3 records.
- `test_status_coverage` — each of the 5 given statuses has ≥1 record.
- `test_fraud_band` — 10 ≤ fraud % ≤ 30.
- `test_field_types_and_ranges` — all 6 fields present with right types; days 0–30;
  amount inside its category range and a multiple of 1000.
- `test_validate_reports_violation` — `validate(records[:10])` returns a non-empty list.
- `test_records_by_id` — lookup by id round-trips.

## Steps
- [ ] Implement `dataset.py` constants, `generate`, `stats`, `validate`
- [ ] Run `uv run python dataset.py`; iterate seed/weights until VALID
- [ ] Add transcript output in `main()`
- [ ] Write `tests/test_dataset.py`
- [ ] Run Verify; fill DECISIONS keys; update PROGRESS; commit

## Verify
1. `uv run python dataset.py` → exits 0, prints `VALID`, category counts all ≥3,
   status counts all ≥1, fraud % between 10 and 30.
2. Run it twice; output identical (determinism).
3. `uv run pytest tests/test_dataset.py -q` → all pass.
4. `transcripts/part1_dataset.md` exists and contains the three tables.

## Record in DECISIONS.md
`dataset_seed`, `dataset_n`, `category_weights`, `status_weights`, `amount_ranges_inr`
(+ rationale), `fraud_probability`, `dataset_stats` (exact counts and fraud %).

## Pitfalls
- Using `random.seed()` globally breaks determinism once other modules use `random`.
- `round(x, -3)` can push a value outside `[lo, hi]` only if lo/hi aren't multiples of
  1000 — keep the ranges as multiples of 1000.
- Print ₹ only via the transcript/stdout; on Windows consoles set `PYTHONUTF8=1` if needed.

## Commit
`plan 01: seeded loan-application dataset generator with validation`
