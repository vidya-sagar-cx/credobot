# Plan 06 — Loan-status tool & designed escalation score

## Goal
`check_loan_application_status(record_id) -> dict` over `dataset.LOAN_APPLICATIONS`, with
a designed, justified `escalation_score ∈ [0, 1]` and a data-derived escalation threshold.

## Brief tasks
T6. Acceptance: "`check_loan_application_status` correctly looks up a record and correctly
computes a designed, justified `escalation_score` (not a bare boolean OR)."

## Depends on
01 (`dataset.RECORDS_BY_ID`, `LOAN_APPLICATIONS`)

## Read first
`dataset.py`, DECISIONS `dataset_stats`.

## Files
```
+ credobot/tools/loan_status.py
+ tests/test_loan_status.py
+ transcripts/part2_escalation.md   (generated)
```

## Code changes — `credobot/tools/loan_status.py`
Plain Python (no CrewAI import here; the CrewAI `BaseTool` wrapper is in plan 08).
```python
from dataset import LOAN_APPLICATIONS, RECORDS_BY_ID

RECORD_ID_RE = re.compile(r"\bLA-\d{4}\b", re.IGNORECASE)
FRAUD_WEIGHT = 0.55
RECENCY_WEIGHT = 0.45
MAX_DAYS = 30
TERMINAL_STATUSES = {"Rejected", "Disbursed"}
TERMINAL_RECENCY_FACTOR = 0.5
ESCALATION_PERCENTILE = 80

def recency_signal(days_since_created: int, status: str) -> float:
    """Normalised age in [0,1]: days/30. Older open applications are more urgent
    (SLA pressure); for terminal statuses the signal is halved."""
    r = min(max(days_since_created, 0), MAX_DAYS) / MAX_DAYS
    return r * (TERMINAL_RECENCY_FACTOR if status in TERMINAL_STATUSES else 1.0)

def escalation_score(record) -> float:
    s = FRAUD_WEIGHT * float(record["flagged_for_fraud_review"]) \
        + RECENCY_WEIGHT * recency_signal(record["days_since_created"], record["status"])
    return round(min(max(s, 0.0), 1.0), 3)

def _percentile(values, pct) -> float   # nearest-rank, stdlib only

ALL_SCORES = sorted(escalation_score(r) for r in LOAN_APPLICATIONS)
ESCALATION_THRESHOLD = round(max(_percentile(ALL_SCORES, ESCALATION_PERCENTILE), 0.55), 3)
# Floor 0.55 = FRAUD_WEIGHT → recency alone (max 0.45) can never trigger escalation;
# a fraud flag is necessary, and fraud + age pushes it over. Recompute & justify from data.

def normalize_record_id(raw: str) -> str | None   # find LA-#### anywhere, upper-case it

def check_loan_application_status(record_id: str) -> dict:
    """Returns {record_id, category, status, loan_amount_inr, days_since_created,
    flagged_for_fraud_review, escalation_score, escalation_threshold, escalate}
    or {"record_id": record_id, "error": "not_found"} / {"error": "invalid_record_id"}.
    counters.incr('tool.check_loan_application_status')."""

def distribution_report() -> dict:
    """min/median/p80/p90/max of scores, p80 of days_since_created, count escalated,
    % escalated, and a histogram in 0.1 buckets. Used for the README justification."""

def main()   # python -m credobot.tools.loan_status → transcripts/part2_escalation.md
```
Design note (goes in transcript + DECISIONS): the weights mean fraud dominates; among
fraud-flagged applications, older open ones rank highest. The threshold is the 80th
percentile of *this dataset's* score distribution (floored at 0.55); the transcript
must state the actual percentile value, what fraction of records it escalates, and the
p80 of `days_since_created` for comparison.

If the computed threshold escalates 0 records or >30 % of records, adjust weights (not
the data) and record why.

## Tests — `tests/test_loan_status.py`
- `test_lookup_known_record` — first record's fields match `dataset.LOAN_APPLICATIONS[0]`.
- `test_lookup_case_and_whitespace` — `" la-1001 "` resolves.
- `test_unknown_record` — `"LA-9999"` → `error == "not_found"`; `"hello"` → `invalid_record_id`.
- `test_score_bounds` — all scores in [0, 1].
- `test_score_formula_examples` — fraud=True, days=30, status Under Review → 1.0;
  fraud=False, days=0 → 0.0; fraud=False, days=30, Disbursed → 0.225; fraud=True, days=15,
  Submitted → 0.775.
- `test_not_bare_boolean_or` — two fraud-flagged records with different days get
  different scores; non-fraud records can have non-zero score.
- `test_threshold_from_distribution` — threshold == max(p80, 0.55) of `ALL_SCORES`;
  escalated share between 1 record and 30 %.
- `test_counter_increments`.

## Steps
- [x] Implement module + `distribution_report`
- [x] Run main; check escalated share; adjust weights only if needed
- [x] Tests; Verify; DECISIONS; PROGRESS; commit

## Verify
1. `uv run python -m credobot.tools.loan_status` → prints formula, distribution stats,
   threshold, escalated count; writes `transcripts/part2_escalation.md` with 3 example
   lookups (one escalated, one not, one unknown id).
2. `uv run pytest tests/test_loan_status.py -q` → pass.

## Record in DECISIONS.md
`escalation_formula`, `escalation_threshold` (value + percentile + % escalated + p80 days).

## Pitfalls
- Importing `dataset` requires repo root on `sys.path`; `uv run` from repo root handles
  it. In tests, `pyproject` `pythonpath = ["."]` under `[tool.pytest.ini_options]` —
  add it if missing.
- Don't hand-tune the threshold to a "nice" number; derive and then explain it.

## Commit
`plan 06: loan status lookup tool with designed escalation score`
