# Decisions & measured values

Values produced by one plan and consumed by later ones. Fill each `TBD` from the plan
that owns it (column **Owner**) using numbers you actually measured/generated — never
invent them. If you later change a value, update every consumer plan and note it in the
change log at the bottom.

| Key | Value | Owner | Consumers | Notes |
|---|---|---|---|---|
| `python_version` | 3.12 | 00 | all | pinned in `.python-version` |
| `pkg_versions` | crewai 1.15.37, autogen-agentchat 0.7.5, autogen-ext 0.7.5, chromadb 1.5.9, sentence-transformers 6.2.0, langchain-core 1.7.6, fastapi 0.162.2 | 00 | 07, 08, 13 | locked via uv sync |
| `dataset_seed` | TBD | 01 | 06, 17 | |
| `dataset_n` | TBD | 01 | 06, 17 | |
| `category_weights` | TBD | 01 | 17 | |
| `status_weights` | TBD | 01 | 17 | |
| `amount_ranges_inr` | TBD | 01 | 17 | per category, + 1-sentence rationale |
| `fraud_probability` | TBD | 01 | 17 | |
| `dataset_stats` | TBD | 01 | 17 | counts per category, per status, fraud % |
| `kb_doc_ids` | TBD | 02 | 03, 05, 16 | list of filenames without `.md` |
| `embed_model` | sentence-transformers/all-MiniLM-L6-v2 | 03 | 04, 09 | |
| `fixed_chunk_params` | TBD (size/overlap chars) | 03 | 05, 17 | |
| `sentence_chunk_params` | TBD (max sentences) | 03 | 05, 17 | |
| `chunk_counts` | TBD (kb_fixed / kb_sentence) | 03 | 17 | |
| `calibration_sims` | TBD (per query, per collection) | 04 | 17 | |
| `idk_threshold` | TBD | 04 | 08, 09, 16, 17 | also in `credobot/config.py` |
| `top_k` | 3 | 04 | 05, 08 | |
| `chunking_pr_results` | TBD (macro P/R per collection) | 05 | 17 | |
| `deploy_collection` | TBD (`kb_fixed` or `kb_sentence`) | 05 | 08, 09, 11, 14 | also in `credobot/config.py` |
| `escalation_formula` | TBD | 06 | 08, 17 | |
| `escalation_threshold` | TBD + percentile justification | 06 | 08, 17 | |
| `support_threshold` | TBD (sentence-level groundedness) | 09 | 13, 16 | |
| `max_request_tokens` | TBD | 10 | 14, 15 | |
| `max_request_cost_usd` | TBD | 10 | 14, 15 | |
| `price_per_1k_tokens_usd` | TBD (nominal) | 10 | 14 | |
| `risk_level` | High (expected) | 10 | 17 | |
| `eval_averages` | TBD (accuracy/grounding/completeness/safety) | 16 | 17 | |

## Change log
| Date | Plan | Change |
|---|---|---|
| 2026-11-08 | 00 | Record locked package versions |
