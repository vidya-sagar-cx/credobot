"""Unit tests for loan status lookup and escalation scoring."""
from credobot import counters
from credobot.tools.loan_status import (
    ALL_SCORES,
    ESCALATION_THRESHOLD,
    _percentile,
    check_loan_application_status,
    escalation_score,
)
from dataset import LOAN_APPLICATIONS


def test_lookup_known_record():
    first = LOAN_APPLICATIONS[0]
    res = check_loan_application_status(first["record_id"])
    assert res["record_id"] == first["record_id"]
    assert res["category"] == first["category"]
    assert res["status"] == first["status"]
    assert res["loan_amount_inr"] == first["loan_amount_inr"]
    assert res["days_since_created"] == first["days_since_created"]
    assert res["flagged_for_fraud_review"] == first["flagged_for_fraud_review"]
    assert "escalation_score" in res
    assert "escalate" in res


def test_lookup_case_and_whitespace():
    first_id = LOAN_APPLICATIONS[0]["record_id"]
    noisy_id = f"  {first_id.lower()}  "
    res = check_loan_application_status(noisy_id)
    assert res["record_id"] == first_id


def test_unknown_record():
    res_unknown = check_loan_application_status("LA-9999")
    assert res_unknown.get("error") == "not_found"

    res_invalid = check_loan_application_status("hello world")
    assert res_invalid.get("error") == "invalid_record_id"


def test_score_bounds():
    for r in LOAN_APPLICATIONS:
        s = escalation_score(r)
        assert 0.0 <= s <= 1.0


def test_score_formula_examples():
    # 1. fraud=True, days=30, status Under Review -> 1.0
    r1 = {"flagged_for_fraud_review": True, "days_since_created": 30, "status": "Under Review"}
    assert escalation_score(r1) == 1.0

    # 2. fraud=False, days=0 -> 0.0
    r2 = {"flagged_for_fraud_review": False, "days_since_created": 0, "status": "Submitted"}
    assert escalation_score(r2) == 0.0

    # 3. fraud=False, days=30, Disbursed -> 0.225
    r3 = {"flagged_for_fraud_review": False, "days_since_created": 30, "status": "Disbursed"}
    assert escalation_score(r3) == 0.225

    # 4. fraud=True, days=15, Submitted -> 0.775
    r4 = {"flagged_for_fraud_review": True, "days_since_created": 15, "status": "Submitted"}
    assert escalation_score(r4) == 0.775


def test_not_bare_boolean_or():
    # Two fraud-flagged records with different days get different scores
    rf1 = {"flagged_for_fraud_review": True, "days_since_created": 5, "status": "Under Review"}
    rf2 = {"flagged_for_fraud_review": True, "days_since_created": 25, "status": "Under Review"}
    assert escalation_score(rf1) != escalation_score(rf2)

    # Non-fraud records have non-zero scores when days > 0
    rn = {"flagged_for_fraud_review": False, "days_since_created": 10, "status": "Submitted"}
    assert escalation_score(rn) > 0.0


def test_threshold_from_distribution():
    p80 = _percentile(ALL_SCORES, 80)
    expected_threshold = round(max(p80, 0.55), 3)
    assert ESCALATION_THRESHOLD == expected_threshold

    escalated = [r for r in LOAN_APPLICATIONS if escalation_score(r) >= ESCALATION_THRESHOLD]
    escalated_share = len(escalated) / len(LOAN_APPLICATIONS)
    assert 1 <= len(escalated)
    assert escalated_share <= 0.30


def test_counter_increments():
    counters.reset("tool.check_loan_application_status")
    assert counters.get("tool.check_loan_application_status") == 0
    check_loan_application_status("LA-1001")
    assert counters.get("tool.check_loan_application_status") == 1
