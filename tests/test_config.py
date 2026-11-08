import os
from pathlib import Path
import pytest
from credobot import config, counters
from credobot.demos.transcript import Transcript


def test_telemetry_disabled_by_default():
    assert os.environ.get("CREWAI_DISABLE_TELEMETRY") == "true"
    assert os.environ.get("OTEL_SDK_DISABLED") == "true"


def test_mock_llm_default_true():
    assert config.MOCK_LLM is True


def test_paths_absolute():
    assert config.CHROMA_DIR.is_absolute()
    assert config.LOG_DIR.is_absolute()
    assert config.KB_DIR.is_absolute()


def test_counters_roundtrip():
    counters.reset()
    assert counters.get("test.counter") == 0
    counters.incr("test.counter")
    assert counters.get("test.counter") == 1
    counters.incr("test.counter", 4)
    assert counters.get("test.counter") == 5

    snap = counters.snapshot()
    assert snap == {"test.counter": 5}
    snap["test.counter"] = 999
    assert counters.get("test.counter") == 5  # snapshot must be a copy

    counters.reset("other.counter")
    assert counters.get("test.counter") == 5
    counters.reset("test.counter")
    assert counters.get("test.counter") == 0


def test_transcript_writes_utf8(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TRANSCRIPTS_DIR", tmp_path / "transcripts")
    t = Transcript("sample_demo", "Sample Title")
    t.para("Disbursed loan amount: ₹1,00,000")
    out_path = t.save()

    assert out_path.exists()
    content_bytes = out_path.read_bytes()
    assert b"\r\n" not in content_bytes  # LF line endings
    content_str = out_path.read_text(encoding="utf-8")
    assert "₹1,00,000" in content_str
    assert "Sample Title" in content_str

