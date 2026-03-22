from __future__ import annotations

from dataclasses import asdict

from src.adapters.persistence.database import MetadataDatabase
from src.adapters.persistence.records import DeanonymizationSessionRecord


class DeanonymizationSessionRepository:
    def __init__(self, database: MetadataDatabase) -> None:
        self._database = database

    def create(self, record: DeanonymizationSessionRecord) -> DeanonymizationSessionRecord:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO deanonymization_sessions (
                    session_id, case_id, created_at, mapping_revision_used, input_preview_snippet,
                    result_preview_snippet, match_count, session_status, exported_artifact_id
                ) VALUES (
                    :session_id, :case_id, :created_at, :mapping_revision_used, :input_preview_snippet,
                    :result_preview_snippet, :match_count, :session_status, :exported_artifact_id
                )
                """,
                asdict(record),
            )
            connection.commit()
        return record
