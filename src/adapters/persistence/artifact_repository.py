from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import sqlite3

from src.adapters.persistence.database import MetadataDatabase
from src.adapters.persistence.records import ArtifactRecord


class ArtifactRepository:
    def __init__(self, database: MetadataDatabase) -> None:
        self._database = database

    @staticmethod
    def _from_row(row) -> ArtifactRecord:
        return ArtifactRecord(**dict(row))

    def create(self, record: ArtifactRecord, *, connection: sqlite3.Connection | None = None) -> ArtifactRecord:
        owns_connection = connection is None
        db_connection = connection or self._database.connect()
        try:
            db_connection.execute(
                """
                INSERT INTO artifacts (
                    artifact_id, case_id, document_id, artifact_type, display_name, file_path,
                    created_at, mapping_revision_used, artifact_status, stale_reason,
                    supersedes_artifact_id, preview_snippet, job_id, mapping_path, content_sha256
                ) VALUES (
                    :artifact_id, :case_id, :document_id, :artifact_type, :display_name, :file_path,
                    :created_at, :mapping_revision_used, :artifact_status, :stale_reason,
                    :supersedes_artifact_id, :preview_snippet, :job_id, :mapping_path, :content_sha256
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

    def list_by_case(self, case_id: str) -> list[ArtifactRecord]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM artifacts WHERE case_id = ? ORDER BY created_at DESC",
                (case_id,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def get(self, artifact_id: str) -> ArtifactRecord | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM artifacts WHERE artifact_id = ?",
                (artifact_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def list_by_document(self, document_id: str) -> list[ArtifactRecord]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM artifacts WHERE document_id = ? ORDER BY created_at DESC",
                (document_id,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def list_linked_for_review(self, case_id: str) -> list[ArtifactRecord]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM artifacts
                WHERE case_id = ? AND document_id IS NOT NULL AND mapping_path IS NOT NULL
                ORDER BY created_at ASC, artifact_id ASC
                """,
                (case_id,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def update_state(
        self,
        *,
        artifact_id: str,
        artifact_status: str,
        stale_reason: str | None,
        supersedes_artifact_id: str | None,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        owns_connection = connection is None
        db_connection = connection or self._database.connect()
        try:
            db_connection.execute(
                """
                UPDATE artifacts
                SET artifact_status = ?, stale_reason = ?, supersedes_artifact_id = ?
                WHERE artifact_id = ?
                """,
                (artifact_status, stale_reason, supersedes_artifact_id, artifact_id),
            )
            if owns_connection:
                db_connection.commit()
        finally:
            if owns_connection:
                db_connection.close()

    def list_missing_ids(self, case_id: str) -> set[str]:
        return {
            record.artifact_id
            for record in self.list_by_case(case_id)
            if not Path(record.file_path).exists()
        }

    def list_missing_records(self, case_id: str) -> tuple[ArtifactRecord, ...]:
        return tuple(
            record
            for record in self.list_by_case(case_id)
            if not Path(record.file_path).exists()
        )

    def list_tracked_file_paths(self, case_id: str) -> tuple[Path, ...]:
        return tuple(Path(record.file_path) for record in self.list_by_case(case_id))
