from __future__ import annotations

from pathlib import Path
import sqlite3
import pytest

from src.adapters.persistence.case_repository import CaseRepository
from src.adapters.persistence.database import MetadataDatabase
from src.adapters.persistence.document_repository import DocumentRepository

REPO_ROOT = Path(__file__).resolve().parents[3]


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
        REPO_ROOT / "src/adapters/persistence/case_repository.py",
        REPO_ROOT / "src/adapters/persistence/document_repository.py",
        REPO_ROOT / "src/adapters/persistence/mapping_revision_repository.py",
        REPO_ROOT / "src/adapters/persistence/job_repository.py",
        REPO_ROOT / "src/adapters/persistence/artifact_repository.py",
    ]

    for path in repo_files:
        content = path.read_text(encoding="utf-8")
        assert "src.services" not in content


def test_sqlite_foreign_keys_are_enforced(tmp_path: Path) -> None:
    database = MetadataDatabase(tmp_path / "metadata.sqlite3")
    database.bootstrap()

    with database.connect() as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO documents (
                    document_id, case_id, source_filename, source_display_path, imported_copy_path,
                    source_fingerprint, preview_snippet, imported_at, last_processed_at,
                    document_status, last_error_summary, latest_output_artifact_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "doc-1",
                    "missing-case",
                    "piece.txt",
                    "/tmp/piece.txt",
                    None,
                    "abc",
                    "snippet",
                    "2026-03-22T00:00:00+00:00",
                    None,
                    "new",
                    None,
                    None,
                ),
            )
