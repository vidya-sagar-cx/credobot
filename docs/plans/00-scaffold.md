# Plan 00 — Scaffold & tooling

## Goal
A uv-managed Python 3.12 project with all dependencies locked, the `credobot` package
skeleton, a config module that enforces zero-network defaults, shared counters and
transcript helpers, a pytest setup, and cross-platform repo hygiene files. No feature
code yet.

## Brief tasks
None directly; enables every task. Satisfies the "CREWAI_DISABLE_TELEMETRY set" and
"zero API keys" submission guidelines at the code level.

## Depends on
—

## Read first
`AGENTS.md`, `docs/SETUP.md`, `docs/BRIEF.md` (Submission Guidelines section).

## Files
```
+ pyproject.toml            + .python-version        + .gitattributes
+ .env.example              ~ .gitignore             + uv.lock (generated)
+ credobot/__init__.py      + credobot/config.py     + credobot/counters.py
+ credobot/{llm,rag,tools,crew,guardrails,review,governance,api,eval,demos}/__init__.py
+ credobot/demos/transcript.py
+ tests/__init__.py         + tests/conftest.py      + tests/test_config.py
+ transcripts/.gitkeep      + kb/.gitkeep
```

## Code changes

### `.python-version`
`3.12`

### `pyproject.toml`
Create with `uv init --package --name credobot --python 3.12` *or* by hand, then
`uv add` the deps so versions get locked. Required content:
```toml
[project]
name = "credobot"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = []          # filled by uv add below

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["credobot"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]          # so tests can `import dataset` from repo root
addopts = "-q"
filterwarnings = ["ignore::DeprecationWarning:chromadb.*"]
```
Then:
```
uv add crewai autogen-agentchat autogen-core "autogen-ext[openai]" chromadb \
       sentence-transformers langchain-core fastapi "uvicorn[standard]" pydantic \
       python-dotenv numpy websockets
uv add --dev pytest httpx
```
If `uv` cannot resolve because of a crewai/chromadb pin conflict, let crewai's own
chromadb pin win (`uv add chromadb` without a version) — do not force versions.

### `.gitattributes`
```
* text=auto eol=lf
*.bat text eol=crlf
*.ps1 text eol=crlf
```

### `.gitignore` additions (append, keep existing)
```
.chroma/
logs/
.pytest_cache/
```
(`.env` and `.venv` are already ignored — verify.)

### `.env.example`
All variables from the table in `docs/SETUP.md` §3 with their defaults; secrets empty:
```
MOCK_LLM=true
CREWAI_DISABLE_TELEMETRY=true
OTEL_SDK_DISABLED=true
ANONYMIZED_TELEMETRY=False
# HF_HUB_OFFLINE=1
EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHROMA_DIR=.chroma
LOG_DIR=logs
# MAX_REQUEST_TOKENS=        (set by plan 10)
# MAX_REQUEST_COST_USD=      (set by plan 10)
OPENAI_API_KEY=
OPENAI_BASE_URL=
LLM_MODEL=gpt-4o-mini
```

### `credobot/config.py`
Must have **no heavy imports** (no crewai/chromadb/torch) so importing it first is cheap.
```python
"""Central config. Import this module before crewai/chromadb/autogen anywhere."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=False)

_DEFAULTS = {
    "MOCK_LLM": "true",
    "CREWAI_DISABLE_TELEMETRY": "true",
    "OTEL_SDK_DISABLED": "true",
    "ANONYMIZED_TELEMETRY": "False",
    "CREWAI_TRACING_ENABLED": "false",
}
for _k, _v in _DEFAULTS.items():
    os.environ.setdefault(_k, _v)

def _bool(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}

MOCK_LLM: bool = _bool("MOCK_LLM")
KB_DIR = ROOT / "kb"
TRANSCRIPTS_DIR = ROOT / "transcripts"
CHROMA_DIR = Path(os.environ.get("CHROMA_DIR", ROOT / ".chroma"))
LOG_DIR = Path(os.environ.get("LOG_DIR", ROOT / "logs"))
EMBED_MODEL = os.environ.get("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL") or None
# Filled in by later plans (values recorded in docs/plans/DECISIONS.md):
TOP_K = 3
IDK_THRESHOLD: float | None = None        # plan 04
DEPLOY_COLLECTION: str | None = None      # plan 05
SUPPORT_THRESHOLD: float | None = None    # plan 09
```
Relative `CHROMA_DIR`/`LOG_DIR` env values must resolve against `ROOT`
(`p if p.is_absolute() else ROOT / p`).

### `credobot/counters.py`
Thread-safe named counters used as evidence (LLM calls, Chroma queries, tool calls).
```python
import threading
from collections import Counter
_lock = threading.Lock()
_counts: Counter[str] = Counter()

def incr(name: str, n: int = 1) -> None: ...
def get(name: str) -> int: ...
def snapshot() -> dict[str, int]: ...
def reset(*names: str) -> None:   # no names → reset all
    ...
```
Canonical names (use exactly these everywhere): `llm.generate`, `llm.crew`,
`llm.autogen`, `llm.judge`, `chroma.query`, `tool.rag_lookup`,
`tool.check_loan_application_status`, `cache.hit`, `cache.miss`.

### `credobot/demos/transcript.py`
```python
class Transcript:
    def __init__(self, name: str, title: str): ...   # → transcripts/<name>.md
    def h2(self, text: str) -> None: ...
    def para(self, text: str) -> None: ...
    def code(self, text: str, lang: str = "") -> None: ...
    def kv(self, mapping: dict) -> None: ...          # markdown 2-col table
    def table(self, headers: list[str], rows: list[list]) -> None: ...
    def save(self) -> Path: ...  # writes utf-8, LF, header with UTC timestamp,
                                 # MOCK_LLM value and telemetry env values
```
Also echo each block to stdout so demos are readable in the terminal.

### `tests/conftest.py`
```python
import os
os.environ["MOCK_LLM"] = "true"
from credobot import config  # noqa: E402,F401

@pytest.fixture(autouse=True)
def _reset_counters():
    from credobot import counters
    counters.reset(); yield

@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """Point Chroma and log dirs at tmp_path for tests that write state."""
    monkeypatch.setattr(config, "CHROMA_DIR", tmp_path / "chroma")
    monkeypatch.setattr(config, "LOG_DIR", tmp_path / "logs")
    return tmp_path
```

## Tests — `tests/test_config.py`
- `test_telemetry_disabled_by_default` — `os.environ["CREWAI_DISABLE_TELEMETRY"] == "true"`
  and `OTEL_SDK_DISABLED == "true"` after importing config.
- `test_mock_llm_default_true` — `config.MOCK_LLM is True`.
- `test_paths_absolute` — `CHROMA_DIR`, `LOG_DIR`, `KB_DIR` are absolute.
- `test_counters_roundtrip` — incr/get/reset behave; `snapshot()` returns a copy.
- `test_transcript_writes_utf8(tmp_path, monkeypatch)` — write "₹1,00,000" and read back
  with `encoding="utf-8"`; file uses `\n` line endings.

## Steps
- [x] Create `.python-version`, `pyproject.toml`; run `uv add …` and `uv add --dev …`
- [x] Confirm import smoke test (Verify #2) passes on 3.12
- [x] Create `.gitattributes`, `.env.example`, update `.gitignore`
- [x] Create package skeleton (`__init__.py` in every sub-package)
- [x] Implement `config.py`, `counters.py`, `demos/transcript.py`
- [x] Create `tests/conftest.py`, `tests/test_config.py`
- [x] Run Verify; record `pkg_versions` in DECISIONS.md
- [x] Update PROGRESS row → `done`; commit

## Verify
1. `uv sync` — succeeds, creates `.venv`.
2. Import smoke test (all must print without error):
   ```
   uv run python -c "from credobot import config; import crewai, chromadb, sentence_transformers, autogen_agentchat, langchain_core, fastapi; from crewai.llms.base_llm import BaseLLM; from autogen_agentchat.messages import StructuredMessage; print('ok', crewai.__version__)"
   ```
3. `uv run pytest -q` — all tests in `tests/test_config.py` pass.
4. `uv run python --version` → `Python 3.12.x`.
5. `git status` shows `uv.lock` staged; no `.venv`/`.env` tracked.

## Record in DECISIONS.md
`pkg_versions` (output of `uv tree --depth 1`, the 7 key packages).

## Pitfalls
- Don't use Python 3.13/3.14 — crewai/autogen wheels may be missing.
- `config.py` must not import crewai/chromadb (it must run *before* them).
- Windows: never write files without `encoding="utf-8"`.

## Commit
`plan 00: scaffold uv project, config, counters, transcript helper, pytest`
