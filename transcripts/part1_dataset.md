# Part 1 — Loan Application Dataset

- Generated: 2026-11-08T10:38:15.173914+00:00
- MOCK_LLM: True
- CREWAI_DISABLE_TELEMETRY: true
- OTEL_SDK_DISABLED: true

## Design Choices

| Parameter | Value |
| --- | --- |
| Seed | 2026 |
| Records (n) | 60 |
| Categories | Personal Loan, Home Loan, Auto Loan, Education Loan, Business Loan |
| Category Weights | 0.25, 0.20, 0.20, 0.15, 0.20 |
| Statuses | Submitted, Under Review, Approved, Rejected, Disbursed |
| Status Weights | 0.20, 0.25, 0.20, 0.15, 0.20 |
| Fraud Probability | 0.18 |
| Amount Rationale | Ranges mirror typical Indian retail-bank product limits: unsecured personal loans up to ₹25 lakh, home loans ₹10 lakh–₹1.5 crore, vehicle loans up to ₹30 lakh, education up to ₹40 lakh and MSME business loans up to ₹2 crore. |

## Category Distribution

| Category | Count | Target Min | Requirement Met |
| --- | --- | --- | --- |
| Personal Loan | 22 | >= 3 | True |
| Home Loan | 11 | >= 3 | True |
| Auto Loan | 12 | >= 3 | True |
| Education Loan | 6 | >= 3 | True |
| Business Loan | 9 | >= 3 | True |

## Status Distribution

| Status | Count | Target Min | Requirement Met |
| --- | --- | --- | --- |
| Submitted | 6 | >= 1 | True |
| Under Review | 22 | >= 1 | True |
| Approved | 15 | >= 1 | True |
| Rejected | 7 | >= 1 | True |
| Disbursed | 10 | >= 1 | True |

## Fraud Review Distribution

Flagged for fraud review: **12 / 60 (20.0%)** (Target: 10%–30%)

## Validation Result

**VALID**

## First 10 Generated Records

| Record ID | Category | Status | Loan Amount | Days Created | Fraud Flag |
| --- | --- | --- | --- | --- | --- |
| LA-1001 | Personal Loan | Approved | ₹2,197,000 | 20 | False |
| LA-1002 | Personal Loan | Under Review | ₹2,384,000 | 13 | False |
| LA-1003 | Auto Loan | Rejected | ₹2,259,000 | 24 | False |
| LA-1004 | Home Loan | Submitted | ₹2,354,000 | 3 | False |
| LA-1005 | Personal Loan | Submitted | ₹2,106,000 | 21 | False |
| LA-1006 | Home Loan | Under Review | ₹6,983,000 | 25 | False |
| LA-1007 | Education Loan | Approved | ₹3,133,000 | 10 | True |
| LA-1008 | Auto Loan | Under Review | ₹791,000 | 28 | False |
| LA-1009 | Education Loan | Under Review | ₹3,656,000 | 22 | False |
| LA-1010 | Auto Loan | Submitted | ₹2,657,000 | 17 | False |
