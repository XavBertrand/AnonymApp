from __future__ import annotations

from pathlib import Path

from src.adapters.persistence.case_repository import CaseRepository
from src.adapters.persistence.database import MetadataDatabase
from src.adapters.persistence.document_repository import DocumentRepository


def test_persistence_repositories_store_and_fetch_records(tmp_path: Path) -> None:
    database = MetadataDatabase(tmp_path / "metadata.sqlite3")
    database.bootstrap()
    cases = CaseRepository(database)
    documents = DocumentRepository(database)

    case_record = cases.create("Dossier A")
    source_path = tmp_path / "piece.txt"
    source_path.write_text("Alice", encoding="utf-8")
    document_record = documents.create(
        case_id=case_record.case_id,
        source_path=source_path,
        imported_copy_path=source_path,
        source_fingerprint="abc",
        preview_snippet="Alice",
    )

    assert cases.get(case_record.case_id) == case_record
    assert documents.list_by_case(case_record.case_id)[0] == document_record


def test_persistence_modules_stay_data_focused() -> None:
    repo_files = [
        Path("src/adapters/persistence/case_repository.py"),
        Path("src/adapters/persistence/document_repository.py"),
        Path("src/adapters/persistence/mapping_revision_repository.py"),
        Path("src/adapters/persistence/job_repository.py"),
        Path("src/adapters/persistence/artifact_repository.py"),
    ]

    for path in repo_files:
        content = path.read_text(encoding="utf-8")
        assert "src.services" not in content
