# Part 1 — Chunking & Indexing

- Generated: 2026-11-08T07:34:39.830249+00:00
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
| kb_fixed | 62 |
| kb_sentence | 26 |

## Sample Retrieval: 'How is EMI calculated?'

| Collection | Rank | Chunk ID | Doc ID | Cosine Distance | Snippet |
| --- | --- | --- | --- | --- | --- |
| kb_fixed | 1 | fixed:emi_calculation:000 | emi_calculation | 0.5047 | Equated Monthly Installments at X Corp Bank are calculated using the reduci... |
| kb_fixed | 2 | fixed:emi_calculation:003 | emi_calculation | 0.5690 | mount is rounded off to the nearest whole rupee to standardize billing sche... |
| kb_fixed | 3 | fixed:emi_calculation:002 | emi_calculation | 0.5948 | otes the monthly interest rate derived by dividing the annual rate by 12, a... |
| kb_sentence | 1 | sentence:emi_calculation:001 | emi_calculation | 0.3652 | The calculated installment amount is rounded off to the nearest whole rupee... |
| kb_sentence | 2 | sentence:emi_calculation:000 | emi_calculation | 0.5790 | Equated Monthly Installments at X Corp Bank are calculated using the reduci... |
| kb_sentence | 3 | sentence:nri_accounts:001 | nri_accounts | 0.7801 | Funds maintained within NRE and FCNR accounts remain fully and freely repat... |
