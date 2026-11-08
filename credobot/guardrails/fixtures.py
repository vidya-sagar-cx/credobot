"""Test fixtures for guardrail calibration, detection, and evaluation."""

# Fabricated unsupported financial claims with no basis in CRED policy documents:
UNSUPPORTED_CLAIMS: list[str] = [
    "Home loans have zero processing fee and guaranteed instant approval within 15 minutes.",
    "NRI accounts earn a guaranteed 15 percent tax-free annual interest on all savings deposits.",
    "Borrowers with CIBIL score below 400 are automatically eligible for unsecured personal loans up to 50 lakhs.",
    "Gold loans at CRED require no physical collateral or gold valuation appraisal.",
    "All floating rate education loans are completely waived if the student attains higher honors.",
]

# Fabricated PII test strings for testing and validation:
FABRICATED_PII_SAMPLES: list[dict[str, str]] = [
    {
        "type": "PAN",
        "raw": "ABCDE1234F",
        "sample": "My PAN card number is ABCDE1234F for identity verification.",
    },
    {
        "type": "AADHAAR_SPACED",
        "raw": "2345 6789 0123",
        "sample": "Aadhaar number registered is 2345 6789 0123.",
    },
    {
        "type": "AADHAAR_PLAIN",
        "raw": "234567890123",
        "sample": "My 12-digit Aadhaar is 234567890123.",
    },
    {
        "type": "ACCOUNT",
        "raw": "123456789012345",
        "sample": "Credit the funds directly into account 123456789012345.",
    },
]
