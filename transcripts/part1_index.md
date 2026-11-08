# Part 1 — Chunking & Indexing

- Generated: 2026-11-08T10:38:24.234954+00:00
- MOCK_LLM: True
- CREWAI_DISABLE_TELEMETRY: true
- OTEL_SDK_DISABLED: true

## Chunking Strategies Configuration

| Strategy | Collection Name | Parameters |
| --- | --- | --- |
| Fixed-Size with Overlap | kb_fixed | size=200 chars, overlap=50 chars |
| Sentence-Based | kb_sentence | sentences_per_chunk=2 |

## Indexed Chunk Counts

| Collection | Chunk Count |
| --- | --- |
| kb_fixed | 61 |
| kb_sentence | 26 |

## Sample Retrieval: 'How is EMI calculated?'

| Collection | Rank | Chunk ID | Doc ID | Cosine Distance | Snippet |
| --- | --- | --- | --- | --- | --- |
| kb_fixed | 1 | fixed:emi_calculation:000 | emi_calculation | 0.4603 | Equated Monthly Installments at CRED are calculated using the reducing-bala... |
| kb_fixed | 2 | fixed:emi_calculation:003 | emi_calculation | 0.4917 | s rounded off to the nearest whole rupee to standardize billing schedules a... |
| kb_fixed | 3 | fixed:emi_calculation:002 | emi_calculation | 0.5526 | e monthly interest rate derived by dividing the annual rate by 12, and n re... |
| kb_sentence | 1 | sentence:emi_calculation:001 | emi_calculation | 0.3652 | The calculated installment amount is rounded off to the nearest whole rupee... |
| kb_sentence | 2 | sentence:emi_calculation:000 | emi_calculation | 0.5431 | Equated Monthly Installments at CRED are calculated using the reducing-bala... |
| kb_sentence | 3 | sentence:minimum_balance:000 | minimum_balance | 0.7441 | CRED mandates that savings account holders maintain a specified average mon... |
