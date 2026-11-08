"""Standard in-scope and out-of-scope query sets for calibration, evaluation, and demos."""

IN_SCOPE: list[tuple[str, set[str]]] = [
    ("How is the EMI on my loan calculated?", {"emi_calculation"}),
    ("What documents are required to complete KYC?", {"kyc_documents"}),
    ("Is there a penalty if I prepay my home loan early?", {"prepayment_penalty"}),
    ("Who is eligible to open an NRI account?", {"nri_accounts"}),
    ("What is the minimum balance I must keep in a savings account?", {"minimum_balance"}),
    (
        "What credit score do I need for a personal loan and what rate will I get?",
        {"loan_eligibility", "interest_rate_slabs"},
    ),
]

OUT_OF_SCOPE: list[str] = [
    "What is the capital of Australia?",
    "Give me a recipe for chocolate cake.",
    "Who won the 2018 football world cup?",
]
