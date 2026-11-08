# Contributing to CredoBot

Welcome to **CredoBot**! This guide is designed to onboard new engineers, researchers, and contributors quickly so you can understand the codebase, set up your development environment, run tests, and contribute safely and effectively.

---

## 1. Project Overview & Mission

CredoBot is an enterprise loan-support assistant for CRED's lending-operations team. It operates across two primary functional tracks:
1. **Loan Policy Inquiries:** Answering retail banking policy questions using a 13-document knowledge base with dense vector search (`sentence-transformers/all-MiniLM-L6-v2` + `ChromaDB`).
2. **Loan Application Status Checks:** Looking up applicant records from a structured synthetic loan dataset and calculating continuous risk escalation scores.

The platform is designed around strict financial compliance principles:
- **Zero API Keys & Zero Network:** Deterministic local execution (`MOCK_LLM=true`, `CREWAI_DISABLE_TELEMETRY=true`, `OTEL_SDK_DISABLED=true`).
- **Defense-in-Depth Guardrails:** Input PII redaction (PAN, Aadhaar, Account numbers) and prompt-injection filtering; output groundedness entailment verification (`SUPPORT_THRESHOLD=0.81`).
- **Multi-Agent Governance:** 3-agent CrewAI orchestration with least-autonomy tool ACLs and an independent 2-agent AutoGen review team.

For complete architectural details with Mermaid flowcharts and sequence diagrams, read [`architecture.md`](architecture.md).

---

## 2. Repository Layout

```
credobot/
├── architecture.md           # Full system architecture, section-wise deep dives & Mermaid flows
├── README.md                 # Project summary, metrics & acceptance criteria checklist
├── CONTRIBUTING.md           # Onboarding, development workflow & contributing instructions
├── dataset.py                # Deterministic synthetic loan dataset generator (seed 2026, N=60)
├── pyproject.toml            # Python packaging and dependency specifications (uv-managed)
├── uv.lock                   # Deterministically locked dependencies
├── credobot/                 # Core source package
│   ├── config.py             # Central environment and runtime configuration
│   ├── counters.py           # Thread-safe in-memory metrics and telemetry counters
│   ├── cache.py              # Normalized-query LRU response cache with Unicode NFKC keying
│   ├── pipeline.py           # 7-stage end-to-end inference pipeline
│   ├── memory.py             # Multi-turn session memory with entity resolution (LangChain)
│   ├── api/                  # FastAPI web server, WebSocket chat & JSONL logging
│   ├── crew/                 # CrewAI 3-agent orchestration (Retrieval, Lookup, Composer)
│   ├── eval/                 # 15-case evaluation test set and LLM-as-judge scoring engine
│   ├── governance/           # Tool ACL policy, risk classification & runtime cost budget
│   ├── guardrails/           # Input PII masking, injection detector & output groundedness
│   ├── llm/                  # MockLLM (BaseLLM subclass) & real LLM factory
│   ├── rag/                  # Dual chunking, ChromaDB vector indexing & calibrated RAG
│   ├── review/               # AutoGen 2-agent RoundRobinGroupChat review stage
│   └── tools/                # RAG lookup & loan status lookup tools
├── kb/                       # 13 authoritative banking policy markdown documents
├── docs/                     # Documentation
│   ├── SETUP.md              # Cross-platform installation and setup guide
│   ├── REPORT.md             # Technical design decisions and architectural synthesis
│   ├── DECISIONS.md          # Recorded empirical parameters and calibration values
│   └── BRIEF.md              # Capstone brief and requirements
├── tests/                    # Comprehensive pytest test suite (150+ tests)
└── transcripts/              # Graded Markdown transcripts generated offline
    └── INDEX.md              # Master index mapping brief tasks to evidence transcripts
```

---

## 3. Quickstart & Development Environment Setup

We recommend using [`uv`](https://github.com/astral-sh/uv) as the Python package manager. It installs Python 3.12, creates a virtual environment, and locks dependencies deterministically.

### Step 1: Install `uv`
- **macOS / Linux:**
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **Windows (PowerShell):**
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
  *Windows Tip:* Run `git config --global core.longpaths true` once to avoid path length limits.

### Step 2: Clone and Sync
```bash
git clone https://github.com/your-org/credobot.git
cd credobot
uv sync
```
`uv sync` will automatically create `.venv` and install all production and development dependencies.

### Step 3: Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env          # Linux / macOS
Copy-Item .env.example .env   # Windows PowerShell
```
Safe offline defaults are already provided in `credobot/config.py`.

---

## 4. Everyday Development Commands

| Task | Command |
|---|---|
| **Run All Tests** | `uv run pytest -q` |
| **Run Specific Test** | `uv run pytest tests/test_pipeline.py -q` |
| **Start FastAPI Server** | `uv run uvicorn credobot.api.app:app --reload` |
| **Test WebSocket Chat** | `uv run python -m credobot.api.ws_client --session dev-sess` |
| **Regenerate Transcripts** | `uv run python -m credobot.demos.run_all` |
| **Run LLM-as-Judge Evaluation** | `uv run python -m credobot.eval.run_eval` |
| **Inspect Dataset Statistics** | `uv run python dataset.py` |
| **Rebuild Vector Indexes** | `uv run python -m credobot.rag.index` |

---

## 5. Testing & Code Quality Standards

CredoBot maintains high quality and coverage across 20 test modules. When submitting changes, follow these guidelines:

1. **Deterministic Execution:**
   All unit and integration tests must run without requiring network access or external API keys (`MOCK_LLM=true`).
2. **State Isolation:**
   Tests that create or modify index collections or logs must use the `isolated_env` pytest fixture (defined in `tests/conftest.py`) to prevent state bleed.
3. **Guardrail Integrity:**
   Ensure raw PII patterns (`PAN_RE`, `AADHAAR_RE`, `ACCOUNT_RE`) are never leaked in unmasked forms into disk logs or emitted answers.
4. **FastAPI & Async:**
   When writing tests for async endpoints, wrap coroutines with `asyncio.run()` or standard sync test functions.

---

## 6. How to Add a Feature or Contribute

1. **Create a Feature Branch:**
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. **Implement Your Changes:**
   - Adhere to PEP 8 standards and standard Python type hints.
   - Maintain docstrings and file headers.
   - Preserve UTF-8 encoding across Windows, macOS, and Linux.
3. **Verify Everything Locally:**
   ```bash
   # Run full test suite
   uv run pytest -q

   # Verify transcript generation
   uv run python -m credobot.demos.run_all
   ```
4. **Commit with Conventional Messages:**
   Use clear, descriptive commit messages:
   ```bash
   git commit -m "feat(rag): add support for semantic chunk boundary detection"
   ```
5. **Open a Pull Request:**
   Submit your pull request against the `main` branch with a summary of changes and test evidence.

