# Part 2 — Loan Status Tool & Escalation Score

- Generated: 2026-11-08T07:49:12.076918+00:00
- MOCK_LLM: True
- CREWAI_DISABLE_TELEMETRY: true
- OTEL_SDK_DISABLED: true

## Escalation Score Formula & Rationale

**Designed Formula:** `escalation_score = 0.55 * flagged_for_fraud_review + 0.45 * (days_since_created / 30 * (0.5 if status in {Rejected, Disbursed} else 1.0))`

**Design Rationale:** Fraud risk is the primary concern for lending operations, weighted at 0.55. Recency (application vintage) accounts for the remaining 0.45, normalized over the 30-day window. For open loans (Submitted, Under Review, Approved), age creates SLA pressure; for terminal statuses (Disbursed, Rejected), recency urgency is discounted by 50%. The floor of 0.55 ensures that recency alone can never trigger escalation without an active fraud review flag.

## Dataset Distribution Statistics

| Metric | Value |
| --- | --- |
| Total Applications | 60 |
| Min Escalation Score | 0.0 |
| Median Escalation Score (p50) | 0.247 |
| 80th Percentile Score (p80) | 0.473 |
| 90th Percentile Score (p90) | 0.703 |
| Max Escalation Score | 0.985 |
| 80th Percentile days_since_created | 25.0 days |
| Calibrated Threshold | 0.55 |
| Applications Escalated | 12 / 60 (20.0%) |

## Sample Tool Invocations

| Scenario | Query ID | Status | Amount | Days | Fraud? | Score | Escalate? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Escalated Case | LA-1007 | Approved | ₹3,133,000 | 10 | True | 0.7 | **True** |
| Standard Case | LA-1001 | Approved | ₹2,197,000 | 20 | False | 0.3 | **False** |
| Unknown ID | LA-9999 | N/A | N/A | N/A | N/A | N/A | Error: not_found |
