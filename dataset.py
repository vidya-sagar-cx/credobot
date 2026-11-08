"""Loan application dataset generator and validator for CredoBot."""
from collections import Counter
import random
from typing import TypedDict

SEED: int = 2026
N_RECORDS: int = 60
CATEGORIES: list[str] = [
    "Personal Loan",
    "Home Loan",
    "Auto Loan",
    "Education Loan",
    "Business Loan",
]
STATUSES: list[str] = [
    "Submitted",
    "Under Review",
    "Approved",
    "Rejected",
    "Disbursed",
]
CATEGORY_WEIGHTS: list[float] = [0.25, 0.20, 0.20, 0.15, 0.20]
STATUS_WEIGHTS: list[float] = [0.20, 0.25, 0.20, 0.15, 0.20]
FRAUD_PROBABILITY: float = 0.18

AMOUNT_RANGES_INR: dict[str, tuple[int, int]] = {
    "Personal Loan": (50_000, 2_500_000),
    "Home Loan": (1_000_000, 15_000_000),
    "Auto Loan": (200_000, 3_000_000),
    "Education Loan": (100_000, 4_000_000),
    "Business Loan": (500_000, 20_000_000),
}
AMOUNT_RATIONALE: str = (
    "Ranges mirror typical Indian retail-bank product limits: unsecured personal "
    "loans up to ₹25 lakh, home loans ₹10 lakh–₹1.5 crore, vehicle loans up to "
    "₹30 lakh, education up to ₹40 lakh and MSME business loans up to ₹2 crore."
)


class LoanApplication(TypedDict):
    record_id: str
    category: str
    status: str
    loan_amount_inr: int
    days_since_created: int
    flagged_for_fraud_review: bool


def generate(seed: int = SEED, n: int = N_RECORDS) -> list[LoanApplication]:
    """Deterministically generate n loan applications using local RNG."""
    rng = random.Random(seed)
    records: list[LoanApplication] = []
    for i in range(n):
        category = rng.choices(CATEGORIES, CATEGORY_WEIGHTS)[0]
        status = rng.choices(STATUSES, STATUS_WEIGHTS)[0]
        lo, hi = AMOUNT_RANGES_INR[category]
        raw_amount = rng.randint(lo, hi)
        amount = round(raw_amount, -3)
        amount = min(max(amount, lo), hi)
        days = rng.randint(0, 30)
        fraud = rng.random() < FRAUD_PROBABILITY

        records.append(
            LoanApplication(
                record_id=f"LA-{1001 + i}",
                category=category,
                status=status,
                loan_amount_inr=amount,
                days_since_created=days,
                flagged_for_fraud_review=fraud,
            )
        )
    return records


def stats(records: list[LoanApplication]) -> dict:
    """Compute summary statistics for a dataset."""
    n = len(records)
    by_category = dict(Counter(r["category"] for r in records))
    by_status = dict(Counter(r["status"] for r in records))
    fraud_count = sum(1 for r in records if r["flagged_for_fraud_review"])
    fraud_pct = round((fraud_count / n * 100) if n > 0 else 0.0, 2)
    return {
        "n": n,
        "by_category": by_category,
        "by_status": by_status,
        "fraud_count": fraud_count,
        "fraud_pct": fraud_pct,
    }


def validate(records: list[LoanApplication]) -> list[str]:
    """Return list of violated rules (empty == valid)."""
    violations: list[str] = []
    n = len(records)
    if n < 40:
        violations.append(f"Record count {n} < 40")

    cat_counts = Counter(r["category"] for r in records)
    for cat in CATEGORIES:
        if cat_counts.get(cat, 0) < 3:
            violations.append(f"Category '{cat}' count {cat_counts.get(cat, 0)} < 3")

    status_counts = Counter(r["status"] for r in records)
    for stat in STATUSES:
        if status_counts.get(stat, 0) < 1:
            violations.append(f"Status '{stat}' count {status_counts.get(stat, 0)} < 1")

    fraud_count = sum(1 for r in records if r["flagged_for_fraud_review"])
    fraud_pct = (fraud_count / n * 100) if n > 0 else 0.0
    if not (10.0 <= fraud_pct <= 30.0):
        violations.append(f"Fraud review percentage {fraud_pct:.2f}% outside [10.0%, 30.0%]")

    seen_ids = set()
    for r in records:
        rid = r["record_id"]
        if rid in seen_ids:
            violations.append(f"Duplicate record_id: {rid}")
        seen_ids.add(rid)

        days = r["days_since_created"]
        if not (0 <= days <= 30):
            violations.append(f"Record {rid} days_since_created {days} outside [0, 30]")

        amt = r["loan_amount_inr"]
        cat = r["category"]
        if cat in AMOUNT_RANGES_INR:
            lo, hi = AMOUNT_RANGES_INR[cat]
            if not (lo <= amt <= hi):
                violations.append(f"Record {rid} amount {amt} outside range [{lo}, {hi}] for {cat}")

    return violations


LOAN_APPLICATIONS: list[LoanApplication] = generate()
RECORDS_BY_ID: dict[str, LoanApplication] = {r["record_id"]: r for r in LOAN_APPLICATIONS}


def main() -> int:
    """Print dataset statistics and write transcript."""
    s = stats(LOAN_APPLICATIONS)
    violations = validate(LOAN_APPLICATIONS)

    print("=" * 60)
    print("CREDOBOT LOAN APPLICATION DATASET")
    print("=" * 60)
    print(f"Seed: {SEED}")
    print(f"Total Records: {s['n']}")
    print(f"Category Weights: {dict(zip(CATEGORIES, CATEGORY_WEIGHTS))}")
    print(f"Status Weights: {dict(zip(STATUSES, STATUS_WEIGHTS))}")
    print(f"Fraud Probability: {FRAUD_PROBABILITY}")
    print(f"Amount Rationale: {AMOUNT_RATIONALE}")
    print("\nCounts per Category:")
    for cat, cnt in s["by_category"].items():
        print(f"  - {cat}: {cnt}")
    print("\nCounts per Status:")
    for stat, cnt in s["by_status"].items():
        print(f"  - {stat}: {cnt}")
    print(f"\nFraud Review: {s['fraud_count']}/{s['n']} ({s['fraud_pct']}%)")
    print(f"Validation Result: {'VALID' if not violations else 'INVALID'}")
    if violations:
        for v in violations:
            print(f"  [VIOLATION] {v}")
    print("=" * 60)

    try:
        from credobot.demos.transcript import Transcript

        t = Transcript("part1_dataset", "Part 1 — Loan Application Dataset")
        t.h2("Design Choices")
        t.table(
            ["Parameter", "Value"],
            [
                ["Seed", str(SEED)],
                ["Records (n)", str(s["n"])],
                ["Categories", ", ".join(CATEGORIES)],
                ["Category Weights", ", ".join(f"{w:.2f}" for w in CATEGORY_WEIGHTS)],
                ["Statuses", ", ".join(STATUSES)],
                ["Status Weights", ", ".join(f"{w:.2f}" for w in STATUS_WEIGHTS)],
                ["Fraud Probability", f"{FRAUD_PROBABILITY:.2f}"],
                ["Amount Rationale", AMOUNT_RATIONALE],
            ],
        )

        t.h2("Category Distribution")
        t.table(
            ["Category", "Count", "Target Min", "Requirement Met"],
            [[cat, s["by_category"].get(cat, 0), ">= 3", s["by_category"].get(cat, 0) >= 3] for cat in CATEGORIES],
        )

        t.h2("Status Distribution")
        t.table(
            ["Status", "Count", "Target Min", "Requirement Met"],
            [[st, s["by_status"].get(st, 0), ">= 1", s["by_status"].get(st, 0) >= 1] for st in STATUSES],
        )

        t.h2("Fraud Review Distribution")
        t.para(f"Flagged for fraud review: **{s['fraud_count']} / {s['n']} ({s['fraud_pct']}%)** (Target: 10%–30%)")

        t.h2("Validation Result")
        t.para("**VALID**" if not violations else f"**INVALID**: {', '.join(violations)}")

        t.h2("First 10 Generated Records")
        sample_rows = [
            [
                r["record_id"],
                r["category"],
                r["status"],
                f"₹{r['loan_amount_inr']:,}",
                r["days_since_created"],
                str(r["flagged_for_fraud_review"]),
            ]
            for r in LOAN_APPLICATIONS[:10]
        ]
        t.table(
            ["Record ID", "Category", "Status", "Loan Amount", "Days Created", "Fraud Flag"],
            sample_rows,
        )
        saved_path = t.save()
        print(f"Transcript written to: {saved_path}")
    except Exception as e:
        print(f"Failed to generate transcript: {e}")

    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())

