# Decisions & measured values

Values produced by one plan and consumed by later ones. Fill each `TBD` from the plan
that owns it (column **Owner**) using numbers you actually measured/generated — never
invent them. If you later change a value, update every consumer plan and note it in the
change log at the bottom.

| Key | Value | Owner | Consumers | Notes |
|---|---|---|---|---|
| `python_version` | 3.12 | 00 | all | pinned in `.python-version` |
| `pkg_versions` | crewai 1.15.37, autogen-agentchat 0.7.5, autogen-ext 0.7.5, chromadb 1.5.9, sentence-transformers 6.2.0, langchain-core 1.7.6, fastapi 0.162.2 | 00 | 07, 08, 13 | locked via uv sync |
| `dataset_seed` | 2026 | 01 | 06, 17 | Tried 1 seed (seed 2026 passed all checks on first draw) |
| `dataset_n` | 60 | 01 | 06, 17 | Exceeds minimum threshold (>=40) |
| `category_weights` | [0.25, 0.20, 0.20, 0.15, 0.20] | 01 | 17 | Personal: 0.25, Home: 0.20, Auto: 0.20, Education: 0.15, Business: 0.20 |
| `status_weights` | [0.20, 0.25, 0.20, 0.15, 0.20] | 01 | 17 | Submitted: 0.20, Under Review: 0.25, Approved: 0.20, Rejected: 0.15, Disbursed: 0.20 |
| `amount_ranges_inr` | Personal: ₹50k-₹25L, Home: ₹10L-₹1.5Cr, Auto: ₹2L-₹30L, Education: ₹1L-₹40L, Business: ₹5L-₹2Cr | 01 | 17 | Ranges mirror typical Indian retail-bank product limits: unsecured personal loans up to ₹25 lakh, home loans ₹10 lakh–₹1.5 crore, vehicle loans up to ₹30 lakh, education up to ₹40 lakh and MSME business loans up to ₹2 crore. |
| `fraud_probability` | 0.18 | 01 | 17 | Yields 20.0% fraud review rate |
| `dataset_stats` | Categories: Personal=22, Auto=12, Home=11, Business=9, Education=6; Statuses: Under Review=22, Approved=15, Disbursed=10, Rejected=7, Submitted=6; Fraud: 12/60 (20.0%) | 01 | 17 | All categories >= 3; all statuses >= 1; fraud % in [10%, 30%] |
| `kb_doc_ids` | account_closure, credit_card_fees, credit_score_factors, emi_calculation, fraud_dispute, interest_rate_slabs, joint_accounts, kyc_documents, loan_application_process, loan_eligibility, minimum_balance, nri_accounts, prepayment_penalty | 02 | 03, 05, 16 | 13 documents (12 required topics + 1 loan application lifecycle) |
| `embed_model` | sentence-transformers/all-MiniLM-L6-v2 | 03 | 04, 09 | Local 384-dimensional dense embeddings |
| `fixed_chunk_params` | size=200 chars, overlap=50 chars, snap forward max 20 chars | 03 | 05, 17 | Sliding character window with whitespace snapping |
| `sentence_chunk_params` | sentences_per_chunk=2 | 03 | 05, 17 | Consecutive 2-sentence groups without overlap |
| `chunk_counts` | kb_fixed: 62 chunks, kb_sentence: 26 chunks | 03 | 17 | ChromaDB indexed counts across 13 documents |
| `calibration_sims` | fixed: min_in=0.4132, max_out=0.1894, gap=0.2238; sentence: min_in=0.3889, max_out=0.0770, gap=0.3119; overall: min_in=0.3889, max_out=0.1894 | 04 | 17 | 6 in-scope + 3 out-of-scope queries measured |
| `idk_threshold` | 0.29 | 04 | 08, 09, 16, 17 | Midpoint separating overall min_in (0.3889) and max_out (0.1894) |
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
| 2026-11-08 | 01 | Record dataset seed, weights, ranges, rationale, and stats |
| 2026-11-08 | 02 | Record 13 kb_doc_ids |
| 2026-11-08 | 03 | Record chunking parameters and indexed chunk counts (62 fixed, 26 sentence) |
| 2026-11-08 | 04 | Record empirical calibration similarities and IDK_THRESHOLD=0.29 |
