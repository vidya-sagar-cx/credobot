# Part 1 — Grounded Generation Demo

- Generated: 2026-11-08T07:38:10.924192+00:00
- MOCK_LLM: True
- CREWAI_DISABLE_TELEMETRY: true
- OTEL_SDK_DISABLED: true

## Grounded Generation Results (≥5 In-Scope + 1 Out-Of-Scope)

| Query | Sentence Top-1 | Fixed Top-1 | Fallback? | Sources | Answer |
| --- | --- | --- | --- | --- | --- |
| How is the EMI on my loan calculated? | 0.7567 | 0.6061 | False | emi_calculation, loan_application_process | The borrower's first EMI payment date is scheduled exactly one calendar month following loan disbursal or on the immediate designated billing cycle date. Equated Monthly Installments at X Corp Bank are calculated using the reducing-balance amortization formula where EMI equals P multiplied by r multiplied by (1 plus r) to the power n divided by ((1 plus r) to the power n minus 1). |
| What documents are required to complete KYC? | 0.3889 | 0.4132 | False | kyc_documents, loan_eligibility | Under regulatory compliance standards, re-KYC profile reviews are mandatorily scheduled every two years for high-risk customers, every eight years for medium-risk customers, and every ten years for low-risk customers. Customers must also provide one officially valid document as verified proof of identity and current residential address, such as an Aadhaar card, passport, voter identity card, or driving licence. |
| Is there a penalty if I prepay my home loan early? | 0.6175 | 0.5562 | False | interest_rate_slabs, prepayment_penalty | Borrowers may not execute partial prepayment during the first six months from disbursal to preserve initial loan underwriting costs. Individual borrowers holding floating-rate retail loans with X Corp Bank are subject to nil prepayment penalties when making partial or full principal prepayments. |
| Who is eligible to open an NRI account? | 0.4916 | 0.4898 | False | joint_accounts, nri_accounts | Funds maintained within NRE and FCNR accounts remain fully and freely repatriable overseas without regulatory limits or exchange restrictions. Eligible customers may establish Non-Resident External accounts in Indian Rupees, Non-Resident Ordinary accounts for managing domestic Indian income, or Foreign Currency Non-Resident deposits in major global currencies. |
| What is the minimum balance I must keep in a savings account? | 0.6446 | 0.5515 | False | account_closure, minimum_balance | Basic Savings Bank Deposit accounts, student accounts, and corporate salary accounts are completely exempt from minimum balance requirements. X Corp Bank mandates that savings account holders maintain a specified average monthly balance determined by the geographic location of the home branch. |
| What credit score do I need for a personal loan and what rate will I get? | 0.5655 | 0.5590 | False | interest_rate_slabs, loan_eligibility | Personal Loans range from 10.50 percent per annum for credit scores of 750 and above, increasing to 13.00 percent for scores between 700 and 749, and 16.50 percent for scores below 700. Home Loan borrowers require a minimum household income of ₹50,000 per month, an age limit extending up to 65 years at loan maturity, and a minimum credit score of 720. |
| What is the capital of Australia? | 0.0770 | 0.1894 | True | None | I don't know — the X Corp policy knowledge base doesn't cover that. Please contact lending operations. |
