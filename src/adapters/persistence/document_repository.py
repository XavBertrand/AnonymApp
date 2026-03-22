from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from uuid import uuid4

from src.adapters.persistence.database import MetadataDatabase
from src.adapters.persistence.records import DocumentRecord


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DocumentRepository:
    def __init__(self, database: MetadataDatabase) -> None:
        self._database = database

    @staticmethod
    def _from_row(row) -> DocumentRecord:
        return DocumentRecord(**dict(row))

    def create(
        self,
        *,
        case_id: str,
        source_path: Path,
        imported_copy_path: Path | None,
        source_fingerprint: str,
        preview_snippet: str,
        connection: sqlite3.Connection | None = None,
    ) -> DocumentRecord:
        now = _utc_now()
        record = DocumentRecord(
            document_id=uuid4().hex,
            case_id=case_id,
            source_filename=source_path.name,
            source_display_path=str(source_path),
            imported_copy_path=str(imported_copy_path) if imported_copy_path else None,
            source_fingerprint=source_fingerprint,
            preview_snippet=preview_snippet,
            imported_at=now,
            last_processed_at=None,
            document_status="new",
            last_error_summary=None,
            latest_output_artifact_id=None,
        )
        owns_connection = connection is None
        db_connection = connection or self._database.connect()
        try:
            db_connection.execute(
                """
                INSERT INTO documents (
                    document_id, case_id, source_filename, source_display_path, imported_copy_path,
                    source_fingerprint, preview_snippet, imported_at, last_processed_at,
                    document_status, last_error_summary, latest_output_artifact_id
                ) VALUES (
                    :document_id, :case_id, :source_filename, :source_display_path, :imported_copy_path,
                    :source_fingerprint, :preview_snippet, :imported_at, :last_processed_at,
                    :document_status, :last_error_summary, :latest_output_artifact_id
                )
                """,
                asdict(record),
            )
            if owns_connection:
                db_connection.commit()
        finally:
            if owns_connection:
                db_connection.close()
        return record

    def list_by_case(self, case_id: str) -> list[DocumentRecord]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM documents WHERE case_id = ? ORDER BY imported_at ASC",
                (case_id,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def update_processing(
        self,
        *,
        document_id: str,
        document_status: str,
        last_error_summary: str | None,
        latest_output_artifact_id: str | None,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        owns_connection = connection is None
        db_connection = connection or self._database.connect()
        try:
            db_connection.execute(
                """
                UPDATE documents
                SET document_status = ?, last_error_summary = ?, latest_output_artifact_id = ?, last_processed_at = ?
                WHERE document_id = ?
                """,
                (document_status, last_error_summary, latest_output_artifact_id, _utc_now(), document_id),
            )
            if owns_connection:
                db_connection.commit()
        finally:
            if owns_connection:
                db_connection.close()
