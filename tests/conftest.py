import os
os.environ["MOCK_LLM"] = "true"
from credobot import config  # noqa: E402,F401
import pytest


@pytest.fixture(autouse=True)
def _reset_counters():
    from credobot import counters
    counters.reset()
    yield


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """Point Chroma and log dirs at tmp_path for tests that write state."""
    monkeypatch.setattr(config, "CHROMA_DIR", tmp_path / "chroma")
    monkeypatch.setattr(config, "LOG_DIR", tmp_path / "logs")
    return tmp_path

