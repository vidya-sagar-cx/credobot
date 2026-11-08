"""Transcript helper for generating Markdown artifacts."""
from datetime import datetime, timezone
import os
from pathlib import Path
from credobot import config


class Transcript:
    def __init__(self, name: str, title: str):
        self.name = name if not name.endswith(".md") else name[:-3]
        self.title = title
        self.blocks: list[str] = []

    def h2(self, text: str) -> None:
        block = f"## {text}\n"
        self.blocks.append(block)
        print(f"\n## {text}")

    def para(self, text: str) -> None:
        block = f"{text}\n"
        self.blocks.append(block)
        print(text)

    def code(self, text: str, lang: str = "") -> None:
        block = f"```{lang}\n{text}\n```\n"
        self.blocks.append(block)
        print(f"```{lang}\n{text}\n```")

    def kv(self, mapping: dict) -> None:
        rows = [f"| `{k}` | `{v}` |" for k, v in mapping.items()]
        table_str = "| Key | Value |\n|---|---|\n" + "\n".join(rows) + "\n"
        self.blocks.append(table_str)
        print(table_str)

    def table(self, headers: list[str], rows: list[list]) -> None:
        header_line = "| " + " | ".join(str(h) for h in headers) + " |"
        sep_line = "| " + " | ".join("---" for _ in headers) + " |"
        row_lines = ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
        table_str = "\n".join([header_line, sep_line] + row_lines) + "\n"
        self.blocks.append(table_str)
        print(table_str)

    def save(self) -> Path:
        target_dir = config.TRANSCRIPTS_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / f"{self.name}.md"

        now_utc = datetime.now(timezone.utc).isoformat()
        header = (
            f"# {self.title}\n\n"
            f"- Generated: {now_utc}\n"
            f"- MOCK_LLM: {config.MOCK_LLM}\n"
            f"- CREWAI_DISABLE_TELEMETRY: {os.environ.get('CREWAI_DISABLE_TELEMETRY', 'unset')}\n"
            f"- OTEL_SDK_DISABLED: {os.environ.get('OTEL_SDK_DISABLED', 'unset')}\n\n"
        )
        content = header + "\n".join(self.blocks)
        file_path.write_text(content, encoding="utf-8", newline="\n")
        return file_path
