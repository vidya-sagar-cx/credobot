# Environment setup

Works on macOS, Linux and Windows (PowerShell). No paid accounts, no API keys needed.

## 1. Prerequisites
| Tool | Why | Install |
|---|---|---|
| git | clone/commit | <https://git-scm.com/downloads> |
| uv ≥ 0.5 | Python + dependency manager (also installs Python 3.12 for you) | see below |

Install uv:
```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```
```powershell
# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
You do **not** need a system Python. The repo pins Python 3.12 in `.python-version`
(CrewAI/Autogen don't reliably support 3.13+ yet); `uv` downloads it on first use
(`uv python install 3.12` to do it explicitly).

Windows only, once per machine (avoids path-length errors in deep `.venv` paths):
```powershell
git config --global core.longpaths true
```

## 2. Clone and install
```bash
git clone <repo-url> credobot
cd credobot
git switch feat/loan-support-agent   # until merged to main
uv sync                              # creates .venv and installs locked deps (incl. dev)
```
The first `uv sync` downloads PyTorch (CPU) for sentence-transformers — a few hundred MB.

## 3. Environment variables
Copy the template (`.env` is git-ignored):
```bash
cp .env.example .env            # macOS / Linux
```
```powershell
Copy-Item .env.example .env     # Windows
```
`credobot/config.py` loads `.env` (python-dotenv) and applies safe defaults with
`os.environ.setdefault`, so the defaults below apply even without a `.env` file.

| Variable | Default | Meaning |
|---|---|---|
| `MOCK_LLM` | `true` | Deterministic mock LLM for CrewAI, Autogen, generation and judge. Graded runs use `true`. |
| `CREWAI_DISABLE_TELEMETRY` | `true` | Stops CrewAI's outbound telemetry call on `kickoff()`. **Must stay true.** |
| `OTEL_SDK_DISABLED` | `true` | Disables OpenTelemetry export (belt and braces for the above). |
| `ANONYMIZED_TELEMETRY` | `False` | Disables ChromaDB telemetry. |
| `HF_HUB_OFFLINE` | unset | Set to `1` after the embedding model is cached → fully offline. |
| `EMBED_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Local embedding model. |
| `CHROMA_DIR` | `.chroma` | ChromaDB persistence directory (git-ignored). |
| `LOG_DIR` | `logs` | JSON-Lines request logs (git-ignored). |
| `MAX_REQUEST_TOKENS` | see `DECISIONS.md` | Per-request token budget cap (plan 10). |
| `MAX_REQUEST_COST_USD` | see `DECISIONS.md` | Per-request cost cap (plan 10). |
| `OPENAI_API_KEY` | unset | Only when `MOCK_LLM=false`. |
| `OPENAI_BASE_URL` | unset | Any OpenAI-compatible endpoint (OpenAI, Azure-compatible proxy, Ollama `http://localhost:11434/v1`, …). |
| `LLM_MODEL` | `gpt-4o-mini` | Model name for the real-LLM path. |

Per-shell override examples:
```bash
export MOCK_LLM=true HF_HUB_OFFLINE=1
```
```powershell
$env:MOCK_LLM = "true"; $env:HF_HUB_OFFLINE = "1"
```

## 4. First run (one-time model download + index build)
```bash
uv run python dataset.py                     # prints dataset stats + validation
uv run python -m credobot.rag.index          # downloads embedding model once, builds both Chroma collections
```
After this, set `HF_HUB_OFFLINE=1` and everything runs with no network access.
To rebuild the index from scratch, delete the `.chroma/` folder and re-run the index command.

## 5. Everyday commands
| What | Command |
|---|---|
| Tests | `uv run pytest -q` |
| One test file | `uv run pytest tests/test_dataset.py -q` |
| All demos → `transcripts/` | `uv run python -m credobot.demos.run_all` |
| One part's demo | `uv run python -m credobot.demos.part2` |
| Evaluation (15 queries) | `uv run python -m credobot.eval.run_eval` |
| API server | `uv run uvicorn credobot.api.app:app --reload` (docs at <http://127.0.0.1:8000/docs>) |
| WebSocket test client | `uv run python -m credobot.api.ws_client --session demo` |
| Add a dependency | `uv add <pkg>` / `uv add --dev <pkg>` (commit `pyproject.toml` + `uv.lock`) |

Sample HTTP calls:
```bash
curl -s -X POST localhost:8000/ask -H "content-type: application/json" \
  -d '{"query":"What documents do I need for KYC?","session_id":"s1"}'
```
```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/ask -ContentType "application/json" `
  -Body '{"query":"What documents do I need for KYC?","session_id":"s1"}'
```

## 6. Optional: real LLM
```bash
export MOCK_LLM=false OPENAI_API_KEY=sk-... LLM_MODEL=gpt-4o-mini
# optional: export OPENAI_BASE_URL=http://localhost:11434/v1
```
All graded transcripts must still be generated with `MOCK_LLM=true`.

## 7. Troubleshooting
- **`UnicodeEncodeError` on Windows console** (₹ symbol): `$env:PYTHONUTF8 = "1"`.
- **CRLF diffs on Windows**: `.gitattributes` forces LF; run `git add --renormalize .` once if needed.
- **Chroma "database is locked" / stale index**: stop running servers, delete `.chroma/`, rebuild.
- **Model download fails behind a proxy**: set `HTTPS_PROXY`, or pre-download on another
  machine and copy `~/.cache/huggingface` (Windows: `%USERPROFILE%\.cache\huggingface`).
- **Slow first import**: torch/chromadb import takes several seconds; that's normal.
- **`LangChainDeprecationWarning` for `RunnableWithMessageHistory`**: expected, ignore.

## 8. For AI agents
Read [`AGENTS.md`](../AGENTS.md) then [`docs/plans/README.md`](plans/README.md).
