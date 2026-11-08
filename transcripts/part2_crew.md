# Part 2 — CrewAI Multi-Agent Orchestration

- Generated: 2026-11-08T08:25:07.572217+00:00
- MOCK_LLM: True
- CREWAI_DISABLE_TELEMETRY: true
- OTEL_SDK_DISABLED: true

## Crew Architecture Overview

A 3-agent sequential CrewAI crew (Retrieval Agent → Lookup Agent → Response Composer) orchestrates policy RAG retrieval and application record lookup with Pydantic structured output.

## Policy-only Query: 'What documents do I need for KYC?'

**Intent:** `policy` | **Schema Validation:** `PASS`

| Metric / Step | Details |
| --- | --- |
| Query | What documents do I need for KYC? |
| RAG Tool Calls | 1 |
| Lookup Tool Calls | 0 |
| LLM Steps Executed | 4 |
| Sources Used | kyc_documents |
| Application Record | None |
| Escalate Flag | False |

## Raw Agent Traces — Policy-only Query

**Retrieval Agent Output:**

```json
{"answer": "card, passport, voter identity card, or driving licence. Customers must also provide one officially valid document as verified proof of identity and current residential address, such as an Aadhaar card, passport, voter identity card, or driving licence.", "sources": ["kyc_documents"], "grounded": true, "fallback": false, "top_similarity": 0.4085, "context": ["ity bill or municipal tax receipt dated within the prior three months. Under regulatory compliance standards, re-KYC profile reviews are mandatorily scheduled every two years for high-risk customers, every", "card, passport, voter identity card, or driving licence. Current residential address verification can additionally be substantiated with a recent utility bill or municipal tax receipt dated within the", "laration. Customers must also provide one officially valid document as verified proof of identity and current residential address, such as an Aadhaar card, passport, voter identity card, or driving licence."]}
```

**Lookup Agent Output:**

```json
NO_RECORD_ID
```

**Final Validated CrewResponse JSON:**

```json
{
  "answer": "card, passport, voter identity card, or driving licence. Customers must also provide one officially valid document as verified proof of identity and current residential address, such as an Aadhaar card, passport, voter identity card, or driving licence.",
  "intent": "policy",
  "sources": [
    "kyc_documents"
  ],
  "record": null,
  "escalate": false,
  "grounded": true,
  "top_similarity": 0.4085,
  "guardrail_events": []
}
```

## Status-only Query: 'What is the status of application LA-1007?'

**Intent:** `status` | **Schema Validation:** `PASS`

| Metric / Step | Details |
| --- | --- |
| Query | What is the status of application LA-1007? |
| RAG Tool Calls | 1 |
| Lookup Tool Calls | 1 |
| LLM Steps Executed | 5 |
| Sources Used | None |
| Application Record | LA-1007 (Approved) |
| Escalate Flag | True |

## Raw Agent Traces — Status-only Query

**Retrieval Agent Output:**

```json
{"answer": "The loan application lifecycle at X Corp Bank transitions sequentially across five formal operational statuses comprising Submitted, Under Review, Approved, Rejected, and Disbursed. Clear applications progress to Approved and reach Disbursed within 48 hours, while complex cases require managerial escalation to", "sources": ["loan_application_process", "loan_eligibility"], "grounded": true, "fallback": false, "top_similarity": 0.3575, "context": ["The loan application lifecycle at X Corp Bank transitions sequentially across five formal operational statuses comprising Submitted, Under Review, Approved, Rejected, and Disbursed. An application logged", "file is flagged for fraud review and held pending compliance inspection. Clear applications progress to Approved and reach Disbursed within 48 hours, while complex cases require managerial escalation to", "y program with a creditworthy co-applicant, whereas MSME Business Loans require at least three years of audited business operations and a minimum annual turnover of \u20b930,00,000."]}
```

**Lookup Agent Output:**

```json
{"record_id": "LA-1007", "category": "Education Loan", "status": "Approved", "loan_amount_inr": 3133000, "days_since_created": 10, "flagged_for_fraud_review": true, "escalation_score": 0.7, "escalation_threshold": 0.55, "escalate": true}
```

**Final Validated CrewResponse JSON:**

```json
{
  "answer": "Application LA-1007 (Education Loan, ₹3,133,000) is Approved. Escalation score 0.70 — escalated to lending operations.",
  "intent": "status",
  "sources": [],
  "record": {
    "record_id": "LA-1007",
    "category": "Education Loan",
    "status": "Approved",
    "loan_amount_inr": 3133000,
    "days_since_created": 10,
    "flagged_for_fraud_review": true,
    "escalation_score": 0.7,
    "escalate": true
  },
  "escalate": true,
  "grounded": true,
  "top_similarity": 0.3575,
  "guardrail_events": []
}
```

## Mixed Policy & Status Query: 'Can I prepay my loan LA-1001 without penalty?'

**Intent:** `mixed` | **Schema Validation:** `PASS`

| Metric / Step | Details |
| --- | --- |
| Query | Can I prepay my loan LA-1001 without penalty? |
| RAG Tool Calls | 1 |
| Lookup Tool Calls | 1 |
| LLM Steps Executed | 5 |
| Sources Used | prepayment_penalty |
| Application Record | LA-1001 (Approved) |
| Escalate Flag | False |

## Raw Agent Traces — Mixed Policy & Status Query

**Retrieval Agent Output:**

```json
{"answer": "Fixed-rate retail loans entail a prepayment fee of 2 percent on the prepaid principal sum if the repayment occurs after the mandatory six-month initial lock-in period. Borrowers may not execute partial prepayment during the first six months from disbursal to preserve initial loan underwriting costs.", "sources": ["prepayment_penalty"], "grounded": true, "fallback": false, "top_similarity": 0.5355, "context": ["prepayments. Fixed-rate retail loans entail a prepayment fee of 2 percent on the prepaid principal sum if the repayment occurs after the mandatory six-month initial lock-in period. Borrowers may not execute", "x-month initial lock-in period. Borrowers may not execute partial prepayment during the first six months from disbursal to preserve initial loan underwriting costs. Commercial and corporate business term", "Individual borrowers holding floating-rate retail loans with X Corp Bank are subject to nil prepayment penalties when making partial or full principal prepayments. Fixed-rate retail loans entail a prepayment"]}
```

**Lookup Agent Output:**

```json
{"record_id": "LA-1001", "category": "Personal Loan", "status": "Approved", "loan_amount_inr": 2197000, "days_since_created": 20, "flagged_for_fraud_review": false, "escalation_score": 0.3, "escalation_threshold": 0.55, "escalate": false}
```

**Final Validated CrewResponse JSON:**

```json
{
  "answer": "Fixed-rate retail loans entail a prepayment fee of 2 percent on the prepaid principal sum if the repayment occurs after the mandatory six-month initial lock-in period. Borrowers may not execute partial prepayment during the first six months from disbursal to preserve initial loan underwriting costs.\n\nApplication LA-1001 (Personal Loan, ₹2,197,000) is Approved. Escalation score 0.30 — standard processing SLA applies.",
  "intent": "mixed",
  "sources": [
    "prepayment_penalty"
  ],
  "record": {
    "record_id": "LA-1001",
    "category": "Personal Loan",
    "status": "Approved",
    "loan_amount_inr": 2197000,
    "days_since_created": 20,
    "flagged_for_fraud_review": false,
    "escalation_score": 0.3,
    "escalate": false
  },
  "escalate": false,
  "grounded": true,
  "top_similarity": 0.5355,
  "guardrail_events": []
}
```
