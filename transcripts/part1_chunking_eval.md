# Part 1 — Chunking Strategy Evaluation

- Generated: 2026-11-08T07:44:07.812070+00:00
- MOCK_LLM: True
- CREWAI_DISABLE_TELEMETRY: true
- OTEL_SDK_DISABLED: true

## Evaluation Results for Collection: `kb_fixed`

| # | Query | Retrieved Chunks → Docs (Dedup) | Relevant | Hits | Precision | Recall |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | How is the EMI on my loan calculated? | fixed:emi_calculation:000, fixed:emi_calculation:003, fixed:emi_calculation:002 → emi_calculation | emi_calculation | 1 | 1/1 = 1.00 | 1/1 = 1.00 |
| 2 | What documents are required to complete KYC? | fixed:kyc_documents:001, fixed:account_closure:003, fixed:kyc_documents:002 → kyc_documents, account_closure | kyc_documents | 1 | 1/2 = 0.50 | 1/1 = 1.00 |
| 3 | Is there a penalty if I prepay my home loan early? | fixed:prepayment_penalty:001, fixed:prepayment_penalty:000, fixed:prepayment_penalty:002 → prepayment_penalty | prepayment_penalty | 1 | 1/1 = 1.00 | 1/1 = 1.00 |
| 4 | Who is eligible to open an NRI account? | fixed:joint_accounts:003, fixed:nri_accounts:003, fixed:nri_accounts:001 → joint_accounts, nri_accounts | nri_accounts | 1 | 1/2 = 0.50 | 1/1 = 1.00 |
| 5 | What is the minimum balance I must keep in a savings account? | fixed:minimum_balance:000, fixed:minimum_balance:003, fixed:minimum_balance:001 → minimum_balance | minimum_balance | 1 | 1/1 = 1.00 | 1/1 = 1.00 |
| 6 | What credit score do I need for a personal loan and what rate will I get? | fixed:loan_eligibility:001, fixed:interest_rate_slabs:003, fixed:interest_rate_slabs:002 → loan_eligibility, interest_rate_slabs | interest_rate_slabs, loan_eligibility | 2 | 2/2 = 1.00 | 2/2 = 1.00 |

## Evaluation Results for Collection: `kb_sentence`

| # | Query | Retrieved Chunks → Docs (Dedup) | Relevant | Hits | Precision | Recall |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | How is the EMI on my loan calculated? | sentence:emi_calculation:001, sentence:emi_calculation:000, sentence:loan_application_process:000 → emi_calculation, loan_application_process | emi_calculation | 1 | 1/2 = 0.50 | 1/1 = 1.00 |
| 2 | What documents are required to complete KYC? | sentence:kyc_documents:001, sentence:kyc_documents:000, sentence:loan_eligibility:001 → kyc_documents, loan_eligibility | kyc_documents | 1 | 1/2 = 0.50 | 1/1 = 1.00 |
| 3 | Is there a penalty if I prepay my home loan early? | sentence:prepayment_penalty:001, sentence:prepayment_penalty:000, sentence:interest_rate_slabs:001 → prepayment_penalty, interest_rate_slabs | prepayment_penalty | 1 | 1/2 = 0.50 | 1/1 = 1.00 |
| 4 | Who is eligible to open an NRI account? | sentence:joint_accounts:001, sentence:nri_accounts:001, sentence:nri_accounts:000 → joint_accounts, nri_accounts | nri_accounts | 1 | 1/2 = 0.50 | 1/1 = 1.00 |
| 5 | What is the minimum balance I must keep in a savings account? | sentence:minimum_balance:001, sentence:minimum_balance:000, sentence:account_closure:001 → minimum_balance, account_closure | minimum_balance | 1 | 1/2 = 0.50 | 1/1 = 1.00 |
| 6 | What credit score do I need for a personal loan and what rate will I get? | sentence:interest_rate_slabs:001, sentence:interest_rate_slabs:000, sentence:loan_eligibility:001 → interest_rate_slabs, loan_eligibility | interest_rate_slabs, loan_eligibility | 2 | 2/2 = 1.00 | 2/2 = 1.00 |

## Macro Performance Comparison

| Collection | Macro Precision | Macro Recall | Macro F1 |
| --- | --- | --- | --- |
| kb_fixed | 0.8333 | 1.0000 | 0.9091 |
| kb_sentence | 0.5833 | 1.0000 | 0.7368 |

## Recommendation

We recommend deploying `kb_fixed` for production retrieval. In our empirical evaluation across in-scope policy queries, `kb_sentence` achieved a macro-averaged Precision of 0.5833, Recall of 1.0000, and F1 score of 0.7368, compared to `kb_fixed` which achieved Precision of 0.8333, Recall of 1.0000, and F1 score of 0.9091. Sentence-level chunking produces clean syntactic boundaries that eliminate split phrases and guarantee that retrieved passages map cleanly to discrete policy clauses.
