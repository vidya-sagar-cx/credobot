"""Unit tests for dataset generator."""
from dataset import (
    AMOUNT_RANGES_INR,
    CATEGORIES,
    LOAN_APPLICATIONS,
    RECORDS_BY_ID,
    SEED,
    STATUSES,
    generate,
    stats,
    validate,
)


def test_deterministic():
    data1 = generate(SEED)
    data2 = generate(SEED)
    assert data1 == data2
    data_diff = generate(SEED + 1)
    assert data1 != data_diff


def test_min_records():
    assert len(LOAN_APPLICATIONS) >= 40


def test_category_coverage():
    s = stats(LOAN_APPLICATIONS)
    for cat in CATEGORIES:
        assert s["by_category"].get(cat, 0) >= 3


def test_status_coverage():
    s = stats(LOAN_APPLICATIONS)
    for st in STATUSES:
        assert s["by_status"].get(st, 0) >= 1


def test_fraud_band():
    s = stats(LOAN_APPLICATIONS)
    assert 10.0 <= s["fraud_pct"] <= 30.0


def test_field_types_and_ranges():
    for r in LOAN_APPLICATIONS:
        assert isinstance(r["record_id"], str)
        assert r["category"] in CATEGORIES
        assert r["status"] in STATUSES
        assert isinstance(r["loan_amount_inr"], int)
        assert isinstance(r["days_since_created"], int)
        assert isinstance(r["flagged_for_fraud_review"], bool)

        assert 0 <= r["days_since_created"] <= 30
        lo, hi = AMOUNT_RANGES_INR[r["category"]]
        assert lo <= r["loan_amount_inr"] <= hi
        assert r["loan_amount_inr"] % 1000 == 0


def test_validate_reports_violation():
    # Only 10 records fails the n >= 40 check
    violations = validate(LOAN_APPLICATIONS[:10])
    assert len(violations) > 0


def test_records_by_id():
    assert len(RECORDS_BY_ID) == len(LOAN_APPLICATIONS)
    for r in LOAN_APPLICATIONS:
        rid = r["record_id"]
        assert rid in RECORDS_BY_ID
        assert RECORDS_BY_ID[rid] == r
