# Part 1 — Grounded Generation Demo

- Generated: 2026-11-08T10:38:24.878499+00:00
- MOCK_LLM: True
- CREWAI_DISABLE_TELEMETRY: true
- OTEL_SDK_DISABLED: true

## Grounded Generation Results (≥5 In-Scope + 1 Out-Of-Scope)

| Query | Sentence Top-1 | Fixed Top-1 | Fallback? | Sources | Answer |
| --- | --- | --- | --- | --- | --- |
| How is the EMI on my loan calculated? | 0.7567 | 0.6550 | False | emi_calculation, minimum_balance | The borrower's first EMI payment date is scheduled exactly one calendar month following loan disbursal or on the immediate designated billing cycle date. Equated Monthly Installments at CRED are calculated using the reducing-balance amortization formula where EMI equals P multiplied by r multiplied by (1 plus r) to the power n divided by ((1 plus r) to the power n minus 1). |
| What documents are required to complete KYC? | 0.3889 | 0.4765 | False | kyc_documents, loan_eligibility | Under regulatory compliance standards, re-KYC profile reviews are mandatorily scheduled every two years for high-risk customers, every eight years for medium-risk customers, and every ten years for low-risk customers. Customers must also provide one officially valid document as verified proof of identity and current residential address, such as an Aadhaar card, passport, voter identity card, or driving licence. |
| Is there a penalty if I prepay my home loan early? | 0.6176 | 0.5762 | False | loan_application_process, prepayment_penalty | Individual borrowers holding floating-rate retail loans with CRED are subject to nil prepayment penalties when making partial or full principal prepayments. Borrowers may not execute partial prepayment during the first six months from disbursal to preserve initial loan underwriting costs. |
| Who is eligible to open an NRI account? | 0.5022 | 0.5029 | False | joint_accounts, kyc_documents, nri_accounts | Every retail banking customer opening an account or securing credit with CRED must submit a valid Permanent Account Number or an authorized declaration. Eligible customers may establish Non-Resident External accounts in Indian Rupees, Non-Resident Ordinary accounts for managing domestic Indian income, or Foreign Currency Non-Resident deposits in major global currencies. |
| What is the minimum balance I must keep in a savings account? | 0.6598 | 0.6128 | False | account_closure, minimum_balance | CRED mandates that savings account holders maintain a specified average monthly balance determined by the geographic location of the home branch. Basic Savings Bank Deposit accounts, student accounts, and corporate salary accounts are completely exempt from minimum balance requirements. |
| What credit score do I need for a personal loan and what rate will I get? | 0.6452 | 0.6613 | False | interest_rate_slabs, loan_eligibility | Personal Loans range from 10.50 percent per annum for credit scores of 750 and above, increasing to 13.00 percent for scores between 700 and 749, and 16.50 percent for scores below 700. Home Loans offer preferential base rates starting at 8.40 percent for borrowers with scores of 750 or higher, moving up to 9.25 percent for intermediate credit bands. |
| What is the capital of Australia? | 0.1159 | 0.1777 | True | None | I don't know — the CRED policy knowledge base doesn't cover that. Please contact lending operations. |
