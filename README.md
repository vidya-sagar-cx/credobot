# CredoBot

**Track: Finance (Banking & FinTech)**

AI-powered loan-support agent for X Corp's lending-operations team: answers loan-policy
questions from a knowledge base, checks a loan application's status, remembers the
conversation, is guarded against misuse, has its answers reviewed by a second agent team,
and runs under an explicit governance policy. Built with CrewAI, Autogen, ChromaDB,
SentenceTransformers, LangChain memory and FastAPI. Everything runs under a
deterministic `MOCK_LLM` mode with **zero API keys and zero network access**
(`CREWAI_DISABLE_TELEMETRY=true` and `OTEL_SDK_DISABLED=true` are set by default).

> **Status: planning stage.** Implementation is tracked in
> [`docs/plans/PROGRESS.md`](docs/plans/PROGRESS.md). Results sections below are filled
> in by plan 17.

## Getting started
- Environment setup (macOS / Linux / Windows): [`docs/SETUP.md`](docs/SETUP.md)
- Requirements brief: [`docs/BRIEF.md`](docs/BRIEF.md)
- Implementation plans and progress: [`docs/plans/`](docs/plans/)
- Instructions for AI agents and contributors: [`AGENTS.md`](AGENTS.md)

## Results (TODO — filled by plan 17)
- Dataset design choices (seed, category/status weights, amount ranges, counts, fraud %)
- "I don't know" threshold calibration (measured similarities, chosen threshold)
- Chunking strategy precision/recall and recommendation
- Escalation-score formula and threshold justification
- Risk classification and governance controls
- Evaluation averages (Accuracy, Grounding, Completeness, Safety)
- Transcript index
