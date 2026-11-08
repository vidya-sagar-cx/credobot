"""Loan application status lookup and designed escalation score calculation."""
from collections import Counter
import math
import re
from typing import Any
from credobot import counters
from credobot.demos.transcript import Transcript
from dataset import LOAN_APPLICATIONS, RECORDS_BY_ID

RECORD_ID_RE: re.Pattern = re.compile(r"\bLA-\d{4}\b", re.IGNORECASE)
FRAUD_WEIGHT: float = 0.55
RECENCY_WEIGHT: float = 0.45
MAX_DAYS: int = 30
TERMINAL_STATUSES: set[str] = {"Rejected", "Disbursed"}
TERMINAL_RECENCY_FACTOR: float = 0.5
ESCALATION_PERCENTILE: int = 80


def recency_signal(days_since_created: int, status: str) -> float:
    """Normalised age in [0,1]: days/30. Older open applications are more urgent
    (SLA pressure); for terminal statuses the signal is halved."""
    r = min(max(days_since_created, 0), MAX_DAYS) / MAX_DAYS
    return r * (TERMINAL_RECENCY_FACTOR if status in TERMINAL_STATUSES else 1.0)


def escalation_score(record: dict) -> float:
    """Compute designed composite escalation score combining fraud and recency."""
    s = FRAUD_WEIGHT * float(record["flagged_for_fraud_review"]) + (
        RECENCY_WEIGHT * recency_signal(record["days_since_created"], record["status"])
    )
    return round(min(max(s, 0.0), 1.0), 3)


def _percentile(values: list[float], pct: float) -> float:
    """Nearest-rank / linear interpolation percentile implementation."""
    if not values:
        return 0.0
    k = (len(values) - 1) * (pct / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return values[int(k)]
    d0 = values[int(f)] * (c - k)
    d1 = values[int(c)] * (k - f)
    return d0 + d1


ALL_SCORES: list[float] = sorted(escalation_score(r) for r in LOAN_APPLICATIONS)
ESCALATION_THRESHOLD: float = round(
    max(_percentile(ALL_SCORES, ESCALATION_PERCENTILE), 0.55), 3
)


def normalize_record_id(raw: str) -> str | None:
    """Extract and uppercase 'LA-####' from arbitrary text."""
    match = RECORD_ID_RE.search(raw)
    return match.group(0).upper() if match else None


def check_loan_application_status(record_id: str) -> dict[str, Any]:
    """Look up an application by ID and return its status, amount, and escalation metrics."""
    counters.incr("tool.check_loan_application_status")
    norm_id = normalize_record_id(record_id)
    if not norm_id:
        return {"error": "invalid_record_id", "raw_input": record_id}

    record = RECORDS_BY_ID.get(norm_id)
    if not record:
        return {"record_id": norm_id, "error": "not_found"}

    score = escalation_score(record)
    escalate = score >= ESCALATION_THRESHOLD

    return {
        "record_id": record["record_id"],
        "category": record["category"],
        "status": record["status"],
        "loan_amount_inr": record["loan_amount_inr"],
        "days_since_created": record["days_since_created"],
        "flagged_for_fraud_review": record["flagged_for_fraud_review"],
        "escalation_score": score,
        "escalation_threshold": ESCALATION_THRESHOLD,
        "escalate": escalate,
    }


def distribution_report() -> dict[str, Any]:
    """Summary of scores and days distribution across dataset."""
    all_days = sorted(r["days_since_created"] for r in LOAN_APPLICATIONS)
    p80_days = _percentile(all_days, 80)

    escalated_records = [r for r in LOAN_APPLICATIONS if escalation_score(r) >= ESCALATION_THRESHOLD]
    escalated_count = len(escalated_records)
    escalated_pct = round((escalated_count / len(LOAN_APPLICATIONS)) * 100, 2)

    buckets = Counter(int(s * 10) / 10.0 for s in ALL_SCORES)
    hist = {round(b, 1): buckets.get(round(b, 1), 0) for b in [i / 10.0 for i in range(11)]}

    return {
        "min": min(ALL_SCORES),
        "median": round(_percentile(ALL_SCORES, 50), 3),
        "p80": round(_percentile(ALL_SCORES, 80), 3),
        "p90": round(_percentile(ALL_SCORES, 90), 3),
        "max": max(ALL_SCORES),
        "p80_days": p80_days,
        "escalated_count": escalated_count,
        "escalated_pct": escalated_pct,
        "histogram": hist,
    }


def main() -> int:
    """Run escalation distribution analysis and write transcript."""
    rep = distribution_report()
    formula_str = (
        "escalation_score = 0.55 * flagged_for_fraud_review + "
        "0.45 * (days_since_created / 30 * (0.5 if status in {Rejected, Disbursed} else 1.0))"
    )

    print("=" * 70)
    print("LOAN STATUS ESCALATION SCORE ANALYSIS")
    print("=" * 70)
    print(f"Formula: {formula_str}")
    print(f"Distribution: min={rep['min']}, median={rep['median']}, p80={rep['p80']}, p90={rep['p90']}, max={rep['max']}")
    print(f"P80 days_since_created: {rep['p80_days']}")
    print(f"Active Threshold (ESCALATION_THRESHOLD): {ESCALATION_THRESHOLD}")
    print(f"Escalated Applications: {rep['escalated_count']}/{len(LOAN_APPLICATIONS)} ({rep['escalated_pct']}%)")
    print(f"Score Histogram: {rep['histogram']}")
    print("=" * 70)

    # 3 Example lookups: one escalated, one not escalated, one unknown
    escalated_id = next(r["record_id"] for r in LOAN_APPLICATIONS if escalation_score(r) >= ESCALATION_THRESHOLD)
    normal_id = next(r["record_id"] for r in LOAN_APPLICATIONS if escalation_score(r) < ESCALATION_THRESHOLD)
    unknown_id = "LA-9999"

    res_esc = check_loan_application_status(escalated_id)
    res_norm = check_loan_application_status(normal_id)
    res_unk = check_loan_application_status(unknown_id)

    print("\nExample Lookups:")
    print(f"  Escalated ({escalated_id}): {res_esc}")
    print(f"  Normal    ({normal_id}):    {res_norm}")
    print(f"  Unknown   ({unknown_id}):   {res_unk}")

    t = Transcript("part2_escalation", "Part 2 — Loan Status Tool & Escalation Score")
    t.h2("Escalation Score Formula & Rationale")
    t.para(f"**Designed Formula:** `{formula_str}`")
    t.para(
        "**Design Rationale:** Fraud risk is the primary concern for lending operations, weighted at 0.55. "
        "Recency (application vintage) accounts for the remaining 0.45, normalized over the 30-day window. "
        "For open loans (Submitted, Under Review, Approved), age creates SLA pressure; for terminal statuses "
        "(Disbursed, Rejected), recency urgency is discounted by 50%. The floor of 0.55 ensures that recency alone "
        "can never trigger escalation without an active fraud review flag."
    )

    t.h2("Dataset Distribution Statistics")
    t.table(
        ["Metric", "Value"],
        [
            ["Total Applications", str(len(LOAN_APPLICATIONS))],
            ["Min Escalation Score", str(rep["min"])],
            ["Median Escalation Score (p50)", str(rep["median"])],
            ["80th Percentile Score (p80)", str(rep["p80"])],
            ["90th Percentile Score (p90)", str(rep["p90"])],
            ["Max Escalation Score", str(rep["max"])],
            ["80th Percentile days_since_created", f"{rep['p80_days']} days"],
            ["Calibrated Threshold", str(ESCALATION_THRESHOLD)],
            ["Applications Escalated", f"{rep['escalated_count']} / {len(LOAN_APPLICATIONS)} ({rep['escalated_pct']}%)"],
        ],
    )

    t.h2("Sample Tool Invocations")
    t.table(
        ["Scenario", "Query ID", "Status", "Amount", "Days", "Fraud?", "Score", "Escalate?"],
        [
            [
                "Escalated Case",
                res_esc["record_id"],
                res_esc["status"],
                f"₹{res_esc['loan_amount_inr']:,}",
                res_esc["days_since_created"],
                str(res_esc["flagged_for_fraud_review"]),
                str(res_esc["escalation_score"]),
                f"**{res_esc['escalate']}**",
            ],
            [
                "Standard Case",
                res_norm["record_id"],
                res_norm["status"],
                f"₹{res_norm['loan_amount_inr']:,}",
                res_norm["days_since_created"],
                str(res_norm["flagged_for_fraud_review"]),
                str(res_norm["escalation_score"]),
                f"**{res_norm['escalate']}**",
            ],
            [
                "Unknown ID",
                res_unk.get("record_id", unknown_id),
                "N/A",
                "N/A",
                "N/A",
                "N/A",
                "N/A",
                f"Error: {res_unk.get('error')}",
            ],
        ],
    )

    saved = t.save()
    print(f"\nTranscript written to: {saved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
