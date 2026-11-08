# Part 2 — CrewAI Multi-Agent Orchestration

- Generated: 2026-11-08T10:38:28.402865+00:00
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
{"answer": "Customers must also provide one officially valid document as verified proof of identity and current residential address, such as an Aadhaar card, passport, voter identity card, or driving licence. assport, voter identity card, or driving licence.", "sources": ["kyc_documents"], "grounded": true, "fallback": false, "top_similarity": 0.4565, "cache_hit": false, "context": [{"chunk_id": "fixed:kyc_documents:001", "doc_id": "kyc_documents", "text": "n. Customers must also provide one officially valid document as verified proof of identity and current residential address, such as an Aadhaar card, passport, voter identity card, or driving licence. Current", "similarity": 0.4565}, {"chunk_id": "fixed:kyc_documents:003", "doc_id": "kyc_documents", "text": "l or municipal tax receipt dated within the prior three months. Under regulatory compliance standards, re-KYC profile reviews are mandatorily scheduled every two years for high-risk customers, every eight", "similarity": 0.4016}, {"chunk_id": "fixed:kyc_documents:002", "doc_id": "kyc_documents", "text": "assport, voter identity card, or driving licence. Current residential address verification can additionally be substantiated with a recent utility bill or municipal tax receipt dated within the prior three", "similarity": 0.3297}]}
```

**Lookup Agent Output:**

```json
NO_RECORD_ID
```

**Final Validated CrewResponse JSON:**

```json
{
  "answer": "Customers must also provide one officially valid document as verified proof of identity and current residential address, such as an Aadhaar card, passport, voter identity card, or driving licence. assport, voter identity card, or driving licence.",
  "intent": "policy",
  "sources": [
    "kyc_documents"
  ],
  "record": null,
  "escalate": false,
  "grounded": true,
  "top_similarity": 0.4565,
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
{"answer": "The loan application lifecycle at CRED transitions sequentially across five formal operational statuses comprising Submitted, Under Review, Approved, Rejected, and Disbursed. An application logged as Submitted", "sources": ["loan_application_process", "prepayment_penalty"], "grounded": true, "fallback": false, "top_similarity": 0.3703, "cache_hit": false, "context": [{"chunk_id": "fixed:loan_application_process:000", "doc_id": "loan_application_process", "text": "The loan application lifecycle at CRED transitions sequentially across five formal operational statuses comprising Submitted, Under Review, Approved, Rejected, and Disbursed. An application logged as Submitted", "similarity": 0.3703}, {"chunk_id": "fixed:loan_application_process:001", "doc_id": "loan_application_process", "text": "Rejected, and Disbursed. An application logged as Submitted enters initial document intake, moving to Under Review within two to four business days as lending officers examine borrower credentials. If", "similarity": 0.3025}, {"chunk_id": "fixed:prepayment_penalty:004", "doc_id": "prepayment_penalty", "text": "rge of up to 3 percent of the outstanding facility balance.", "similarity": 0.2826}]}
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
  "top_similarity": 0.3703,
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
{"answer": "Borrowers may not execute partial prepayment during the first six months from disbursal to preserve initial loan underwriting costs. Individual borrowers holding floating-rate retail loans with CRED are subject to nil prepayment penalties when making partial or full principal prepayments.", "sources": ["prepayment_penalty"], "grounded": true, "fallback": false, "top_similarity": 0.5667, "cache_hit": false, "context": [{"chunk_id": "fixed:prepayment_penalty:002", "doc_id": "prepayment_penalty", "text": "initial lock-in period. Borrowers may not execute partial prepayment during the first six months from disbursal to preserve initial loan underwriting costs. Commercial and corporate business term loans", "similarity": 0.5667}, {"chunk_id": "fixed:prepayment_penalty:000", "doc_id": "prepayment_penalty", "text": "Individual borrowers holding floating-rate retail loans with CRED are subject to nil prepayment penalties when making partial or full principal prepayments. Fixed-rate retail loans entail a prepayment", "similarity": 0.5396}, {"chunk_id": "fixed:prepayment_penalty:003", "doc_id": "prepayment_penalty", "text": "costs. Commercial and corporate business term loans remain exempt from the retail zero-penalty waiver and attract a contractual early termination charge of up to 3 percent of the outstanding facility", "similarity": 0.5067}]}
```

**Lookup Agent Output:**

```json
{"record_id": "LA-1001", "category": "Personal Loan", "status": "Approved", "loan_amount_inr": 2197000, "days_since_created": 20, "flagged_for_fraud_review": false, "escalation_score": 0.3, "escalation_threshold": 0.55, "escalate": false}
```

**Final Validated CrewResponse JSON:**

```json
{
  "answer": "Borrowers may not execute partial prepayment during the first six months from disbursal to preserve initial loan underwriting costs. Individual borrowers holding floating-rate retail loans with CRED are subject to nil prepayment penalties when making partial or full principal prepayments.\n\nApplication LA-1001 (Personal Loan, ₹2,197,000) is Approved. Escalation score 0.30 — standard processing SLA applies.",
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
  "top_similarity": 0.5667,
  "guardrail_events": []
}
```
