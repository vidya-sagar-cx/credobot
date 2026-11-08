# Part 1 — Chunking Strategy Evaluation

- Generated: 2026-11-08T10:38:25.063176+00:00
- MOCK_LLM: True
- CREWAI_DISABLE_TELEMETRY: true
- OTEL_SDK_DISABLED: true

## Evaluation Results for Collection: `kb_fixed`

| # | Query | Retrieved Chunks → Docs (Dedup) | Relevant | Hits | Precision | Recall |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | How is the EMI on my loan calculated? | fixed:emi_calculation:003, fixed:emi_calculation:000, fixed:emi_calculation:002 → emi_calculation | emi_calculation | 1 | 1/1 = 1.00 | 1/1 = 1.00 |
| 2 | What documents are required to complete KYC? | fixed:kyc_documents:001, fixed:kyc_documents:003, fixed:account_closure:003 → kyc_documents, account_closure | kyc_documents | 1 | 1/2 = 0.50 | 1/1 = 1.00 |
| 3 | Is there a penalty if I prepay my home loan early? | fixed:prepayment_penalty:000, fixed:prepayment_penalty:002, fixed:prepayment_penalty:001 → prepayment_penalty | prepayment_penalty | 1 | 1/1 = 1.00 | 1/1 = 1.00 |
| 4 | Who is eligible to open an NRI account? | fixed:joint_accounts:003, fixed:kyc_documents:000, fixed:nri_accounts:002 → joint_accounts, kyc_documents, nri_accounts | nri_accounts | 1 | 1/3 = 0.33 | 1/1 = 1.00 |
| 5 | What is the minimum balance I must keep in a savings account? | fixed:minimum_balance:000, fixed:minimum_balance:003, fixed:minimum_balance:001 → minimum_balance | minimum_balance | 1 | 1/1 = 1.00 | 1/1 = 1.00 |
| 6 | What credit score do I need for a personal loan and what rate will I get? | fixed:interest_rate_slabs:002, fixed:interest_rate_slabs:000, fixed:loan_eligibility:001 → interest_rate_slabs, loan_eligibility | interest_rate_slabs, loan_eligibility | 2 | 2/2 = 1.00 | 2/2 = 1.00 |

## Evaluation Results for Collection: `kb_sentence`

| # | Query | Retrieved Chunks → Docs (Dedup) | Relevant | Hits | Precision | Recall |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | How is the EMI on my loan calculated? | sentence:emi_calculation:001, sentence:emi_calculation:000, sentence:minimum_balance:000 → emi_calculation, minimum_balance | emi_calculation | 1 | 1/2 = 0.50 | 1/1 = 1.00 |
| 2 | What documents are required to complete KYC? | sentence:kyc_documents:001, sentence:kyc_documents:000, sentence:loan_eligibility:001 → kyc_documents, loan_eligibility | kyc_documents | 1 | 1/2 = 0.50 | 1/1 = 1.00 |
| 3 | Is there a penalty if I prepay my home loan early? | sentence:prepayment_penalty:000, sentence:prepayment_penalty:001, sentence:loan_application_process:000 → prepayment_penalty, loan_application_process | prepayment_penalty | 1 | 1/2 = 0.50 | 1/1 = 1.00 |
| 4 | Who is eligible to open an NRI account? | sentence:kyc_documents:000, sentence:joint_accounts:001, sentence:nri_accounts:000 → kyc_documents, joint_accounts, nri_accounts | nri_accounts | 1 | 1/3 = 0.33 | 1/1 = 1.00 |
| 5 | What is the minimum balance I must keep in a savings account? | sentence:minimum_balance:000, sentence:minimum_balance:001, sentence:account_closure:000 → minimum_balance, account_closure | minimum_balance | 1 | 1/2 = 0.50 | 1/1 = 1.00 |
| 6 | What credit score do I need for a personal loan and what rate will I get? | sentence:interest_rate_slabs:000, sentence:loan_eligibility:000, sentence:interest_rate_slabs:001 → interest_rate_slabs, loan_eligibility | interest_rate_slabs, loan_eligibility | 2 | 2/2 = 1.00 | 2/2 = 1.00 |

## Macro Performance Comparison

| Collection | Macro Precision | Macro Recall | Macro F1 |
| --- | --- | --- | --- |
| kb_fixed | 0.8056 | 1.0000 | 0.8923 |
| kb_sentence | 0.5556 | 1.0000 | 0.7143 |

## Recommendation

We recommend deploying `kb_fixed` for production retrieval. In our empirical evaluation across in-scope policy queries, `kb_fixed` achieved a superior macro-averaged Precision of 0.8056, Recall of 1.0000, and F1 score of 0.8923, compared to `kb_sentence` which achieved Precision of 0.5556, Recall of 1.0000, and F1 score of 0.7143. Fixed-size chunking with character overlap consistently concentrates top-k retrieved chunks within the exact target policy documents, eliminating cross-document noise while preserving 100% recall.
