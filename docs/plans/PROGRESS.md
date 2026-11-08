# Progress tracker

Single source of truth for plan status. Protocol: [`../../AGENTS.md`](../../AGENTS.md).

Status values: `todo` · `in-progress` · `blocked` · `done`.
Find a plan's commit with `git log --oneline --grep "plan NN"`.

| ID | Plan | Tasks | Deps | Status | Owner | Updated | Notes |
|---|---|---|---|---|---|---|---|
| 00 | [Scaffold & tooling](00-scaffold.md) | — | — | done | antigravity | 2026-11-08 | Project scaffolded, deps locked, tests passing |
| 01 | [Loan dataset generator](01-dataset.md) | T1 | 00 | done | antigravity | 2026-11-08 | Seed 2026, 60 records, 20% fraud, valid |
| 02 | [Knowledge base](02-knowledge-base.md) | T2 | 00 | done | antigravity | 2026-11-08 | 13 policy docs, sentence splitter, loader |
| 03 | [Chunking & indexing](03-chunking-index.md) | T3 | 02 | done | antigravity | 2026-11-08 | 62 fixed and 26 sentence chunks indexed |
| 04 | [Retrieval, calibration, grounded generation](04-grounded-generation.md) | T4 | 03 | done | antigravity | 2026-11-08 | IDK_THRESHOLD=0.29, grounded answers verified |
| 05 | [Chunking P/R evaluation](05-chunking-eval.md) | T5 | 04 | done | antigravity | 2026-11-08 | kb_fixed won (F1=0.9091 vs 0.7368), deployed |
| 06 | [Loan status tool & escalation](06-loan-status-tool.md) | T6 | 01 | done | antigravity | 2026-11-08 | Formula + threshold 0.55 escalates 20% |
| 07 | [MockLLM & LLM factory](07-mock-llm.md) | — | 00 | done | antigravity | 2026-11-08 | BaseLLM subclass with pitfall guards & ReAct |
| 08 | [CrewAI crew & structured output](08-crew.md) | T7, T9 | 04, 06, 07 | done | antigravity | 2026-11-08 | Sequential crew, RAG & status tools, CrewResponse validated |
| 09 | [Guardrails](09-guardrails.md) | T10 | 04 | todo | | | |
| 10 | [Governance](10-governance.md) | T15 | 08 | todo | | | |
| 11 | [Response cache](11-cache.md) | T16 | 04 | todo | | | |
| 12 | [Session memory](12-memory.md) | T8 | 08 | todo | | | |
| 13 | [Autogen review stage](13-autogen-review.md) | T14 | 07, 09 | todo | | | |
| 14 | [End-to-end pipeline](14-pipeline.md) | — | 09, 10, 11, 12, 13 | todo | | | |
| 15 | [FastAPI & JSONL logging](15-api-logging.md) | T11, T12 | 14 | todo | | | |
| 16 | [LLM-as-judge evaluation](16-evaluation.md) | T13 | 14 | todo | | | |
| 17 | [Transcripts & final README](17-final-readme.md) | all | 15, 16 | todo | | | |
