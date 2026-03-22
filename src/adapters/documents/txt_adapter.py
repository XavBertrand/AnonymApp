from __future__ import annotations

from pathlib import Path


class TxtDocumentAdapter:
    format_name = "txt"
    suffixes = (".txt",)

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in self.suffixes

    def load(self, path: Path) -> str:
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Input TXT file not found: {path}")
        return path.read_text(encoding="utf-8")

    def save(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
