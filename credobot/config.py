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
_idk_env = os.environ.get("IDK_THRESHOLD")
IDK_THRESHOLD: float = float(_idk_env) if _idk_env else 0.29  # calibrated in plan 04
DEPLOY_COLLECTION: str = os.environ.get("DEPLOY_COLLECTION", "kb_fixed")  # plan 05
_support_env = os.environ.get("SUPPORT_THRESHOLD")
SUPPORT_THRESHOLD: float = float(_support_env) if _support_env else 0.81  # plan 09

# Budget constants (plan 10):
MAX_REQUEST_TOKENS: int = int(os.environ.get("MAX_REQUEST_TOKENS", "6000"))
MAX_REQUEST_COST_USD: float = float(os.environ.get("MAX_REQUEST_COST_USD", "0.01"))
PRICE_PER_1K_TOKENS_USD: float = float(os.environ.get("PRICE_PER_1K_TOKENS_USD", "0.0006"))
PROMPT_OVERHEAD_TOKENS: int = int(os.environ.get("PROMPT_OVERHEAD_TOKENS", "250"))
MAX_OUTPUT_TOKENS: int = int(os.environ.get("MAX_OUTPUT_TOKENS", "500"))
MAX_QUERY_CHARS: int = int(os.environ.get("MAX_QUERY_CHARS", "4000"))

