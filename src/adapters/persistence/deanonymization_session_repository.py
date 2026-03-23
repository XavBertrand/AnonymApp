from __future__ import annotations

from dataclasses import asdict
import sqlite3

from src.adapters.persistence.database import MetadataDatabase
from src.adapters.persistence.records import DeanonymizationSessionRecord


class DeanonymizationSessionRepository:
    def __init__(self, database: MetadataDatabase) -> None:
        self._database = database

    @staticmethod
    def _from_row(row) -> DeanonymizationSessionRecord:
        return DeanonymizationSessionRecord(**dict(row))

    def create(
        self,
        record: DeanonymizationSessionRecord,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> DeanonymizationSessionRecord:
        owns_connection = connection is None
        db_connection = connection or self._database.connect()
        try:
            db_connection.execute(
                """
                INSERT INTO deanonymization_sessions (
                    session_id, case_id, created_at, mapping_revision_used, input_text_path,
                    result_text_path, input_preview_snippet, result_preview_snippet, match_count,
                    session_status, exported_artifact_id
                ) VALUES (
                    :session_id, :case_id, :created_at, :mapping_revision_used, :input_text_path,
                    :result_text_path, :input_preview_snippet, :result_preview_snippet, :match_count,
                    :session_status, :exported_artifact_id
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

    def get(self, session_id: str) -> DeanonymizationSessionRecord | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM deanonymization_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def update_exported_artifact(
        self,
        *,
        session_id: str,
        exported_artifact_id: str | None,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        owns_connection = connection is None
        db_connection = connection or self._database.connect()
        try:
            db_connection.execute(
                """
                UPDATE deanonymization_sessions
                SET exported_artifact_id = ?
                WHERE session_id = ?
                """,
                (exported_artifact_id, session_id),
            )
            if owns_connection:
                db_connection.commit()
        finally:
            if owns_connection:
                db_connection.close()
