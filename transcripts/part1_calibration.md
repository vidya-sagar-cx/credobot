# Part 1 — IDK Threshold Calibration

- Generated: 2026-11-08T10:38:24.470231+00:00
- MOCK_LLM: True
- CREWAI_DISABLE_TELEMETRY: true
- OTEL_SDK_DISABLED: true

## Empirical Top-1 Cosine Similarity Measurements

| Query | Scope | kb_fixed Top-1 Sim | kb_sentence Top-1 Sim |
| --- | --- | --- | --- |
| How is the EMI on my loan calculated? | IN_SCOPE | 0.6550 | 0.7567 |
| What documents are required to complete KYC? | IN_SCOPE | 0.4765 | 0.3889 |
| Is there a penalty if I prepay my home loan early? | IN_SCOPE | 0.5762 | 0.6176 |
| Who is eligible to open an NRI account? | IN_SCOPE | 0.5029 | 0.5022 |
| What is the minimum balance I must keep in a savings account? | IN_SCOPE | 0.6128 | 0.6598 |
| What credit score do I need for a personal loan and what rate will I get? | IN_SCOPE | 0.6613 | 0.6452 |
| What is the capital of Australia? | OUT_OF_SCOPE | 0.1777 | 0.1159 |
| Give me a recipe for chocolate cake. | OUT_OF_SCOPE | 0.0660 | 0.0374 |
| Who won the 2018 football world cup? | OUT_OF_SCOPE | 0.0728 | 0.0579 |

## Cluster Separation and Calibrated Threshold

| Collection | Min In-Scope Sim | Max Out-Of-Scope Sim | Separation Gap |
| --- | --- | --- | --- |
| kb_fixed | 0.4765 | 0.1777 | 0.2988 |
| kb_sentence | 0.3889 | 0.1159 | 0.2730 |

Overall in-scope minimum is **0.3889** and out-of-scope maximum is **0.1777**.

The calibrated threshold separating both clusters is **`IDK_THRESHOLD = 0.28`**.
