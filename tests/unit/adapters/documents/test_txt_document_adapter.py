from __future__ import annotations

from pathlib import Path

from src.adapters.documents.registry import DocumentAdapterRegistry
from src.adapters.documents.txt_adapter import TxtDocumentAdapter


def test_txt_document_adapter_registry_resolves_txt_files(tmp_path: Path) -> None:
    adapter = TxtDocumentAdapter()
    registry = DocumentAdapterRegistry([adapter])
    path = tmp_path / "sample.txt"
    path.write_text("bonjour", encoding="utf-8")

    resolved = registry.resolve_for_path(path)

    assert resolved is adapter
    assert registry.supported_formats() == ("txt",)
    assert adapter.can_handle(path) is True
    assert adapter.load(path) == "bonjour"


def test_txt_document_adapter_saves_content(tmp_path: Path) -> None:
    adapter = TxtDocumentAdapter()
    destination = tmp_path / "out.txt"

    adapter.save(destination, "contenu")

    assert destination.read_text(encoding="utf-8") == "contenu"
