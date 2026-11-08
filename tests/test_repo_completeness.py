"""Completeness and policy verification tests for repository deliverables."""
import re
import subprocess
from pathlib import Path
import pytest

from credobot import config
import dataset


def test_readme_mentions_track():
    readme_path = Path("README.md")
    assert readme_path.exists(), "README.md must exist in root"
    content = readme_path.read_text(encoding="utf-8")
    assert "Finance (Banking & FinTech)" in content or "Finance (Banking & FinTech)" in content


def test_readme_has_dataset_choices():
    content = Path("README.md").read_text(encoding="utf-8")
    # Must mention seed
    assert str(dataset.SEED) in content
    # Must mention category weights
    for cat, wt in zip(dataset.CATEGORIES, dataset.CATEGORY_WEIGHTS):
        assert cat in content
        assert str(wt) in content or f"{int(wt*100)}%" in content


def test_readme_mentions_telemetry():
    content = Path("README.md").read_text(encoding="utf-8")
    assert "CREWAI_DISABLE_TELEMETRY=true" in content
    assert "OTEL_SDK_DISABLED=true" in content


def test_readme_has_threshold():
    content = Path("README.md").read_text(encoding="utf-8")
    assert str(config.IDK_THRESHOLD) in content


def test_all_transcripts_exist():
    index_path = config.TRANSCRIPTS_DIR / "INDEX.md"
    assert index_path.exists(), "transcripts/INDEX.md must exist"
    index_content = index_path.read_text(encoding="utf-8")

    # Find all transcript links [name.md](name.md) or [name.jsonl](name.jsonl)
    links = re.findall(r"\[`?([a-zA-Z0-9_]+\.(?:md|jsonl))`?\]", index_content)
    assert len(links) >= 15, f"Expected at least 15 transcripts in INDEX.md, found {len(links)}"

    for filename in links:
        file_path = config.TRANSCRIPTS_DIR / filename
        assert file_path.exists(), f"Transcript file {filename} listed in INDEX.md does not exist"
        assert file_path.stat().st_size > 0, f"Transcript file {filename} is empty"


def test_decisions_no_tbd():
    decisions_path = Path("docs/plans/DECISIONS.md")
    assert decisions_path.exists()
    content = decisions_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    for line in lines:
        if line.strip().startswith("|") and not line.strip().startswith("| Key") and not line.strip().startswith("|---"):
            # Ensure no cell in the table contains TBD
            cells = [c.strip() for c in line.split("|")]
            for cell in cells:
                assert cell != "TBD", f"Found unresolved TBD in DECISIONS.md: {line}"


def test_no_images_or_pdfs():
    # Verify no binary assets / images / pdfs are tracked in git
    proc = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    )
    tracked_files = proc.stdout.splitlines()
    forbidden_exts = (".png", ".jpg", ".jpeg", ".gif", ".pdf", ".pptx", ".mp4", ".mov", ".svg")
    for f in tracked_files:
        assert not f.lower().endswith(forbidden_exts), f"Forbidden binary media asset committed: {f}"

