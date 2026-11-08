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
KB_DIR: Path = ROOT / "kb"
TRANSCRIPTS_DIR: Path = ROOT / "transcripts"

_chroma_env = os.environ.get("CHROMA_DIR", ".chroma")
_chroma_path = Path(_chroma_env)
CHROMA_DIR: Path = _chroma_path if _chroma_path.is_absolute() else ROOT / _chroma_path

_log_env = os.environ.get("LOG_DIR", "logs")
_log_path = Path(_log_env)
LOG_DIR: Path = _log_path if _log_path.is_absolute() else ROOT / _log_path

EMBED_MODEL: str = os.environ.get("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
LLM_MODEL: str = os.environ.get("LLM_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL: str | None = os.environ.get("OPENAI_BASE_URL") or None

# Filled in by later plans (values recorded in docs/plans/DECISIONS.md):
TOP_K: int = 3
IDK_THRESHOLD: float | None = None        # plan 04
DEPLOY_COLLECTION: str | None = None      # plan 05
SUPPORT_THRESHOLD: float | None = None    # plan 09
