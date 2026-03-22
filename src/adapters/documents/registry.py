from __future__ import annotations

from pathlib import Path

from src.adapters.documents.contract import DocumentAdapter


class DocumentAdapterRegistry:
    def __init__(self, adapters: list[DocumentAdapter] | None = None) -> None:
        self._by_format: dict[str, DocumentAdapter] = {}
        for adapter in adapters or []:
            self.register(adapter)

    def register(self, adapter: DocumentAdapter) -> None:
        self._by_format[adapter.format_name] = adapter

    def get(self, format_name: str) -> DocumentAdapter:
        try:
            return self._by_format[format_name]
        except KeyError as exc:
            raise ValueError(f"No document adapter registered for format '{format_name}'") from exc

    def resolve_for_path(self, path: Path) -> DocumentAdapter:
        for adapter in self._by_format.values():
            if adapter.can_handle(path):
                return adapter
        raise ValueError(f"No document adapter registered for path '{path}'")

    def supported_formats(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_format))
