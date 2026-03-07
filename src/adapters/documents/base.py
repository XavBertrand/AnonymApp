from __future__ import annotations

from pathlib import Path
from typing import Protocol


class DocumentAdapter(Protocol):
    format_name: str

    def load(self, path: Path) -> str:
        ...

    def save(self, path: Path, content: str) -> None:
        ...
