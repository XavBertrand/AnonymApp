from __future__ import annotations

from dataclasses import asdict

from src.adapters.persistence.database import MetadataDatabase
from src.adapters.persistence.records import ArtifactRecord


class ArtifactRepository:
    def __init__(self, database: MetadataDatabase) -> None:
        self._database = database

    @staticmethod
    def _from_row(row) -> ArtifactRecord:
        return ArtifactRecord(**dict(row))

    def create(self, record: ArtifactRecord) -> ArtifactRecord:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO artifacts (
                    artifact_id, case_id, document_id, artifact_type, display_name, file_path,
                    created_at, mapping_revision_used, artifact_status, stale_reason,
                    supersedes_artifact_id, preview_snippet, job_id, mapping_path
                ) VALUES (
                    :artifact_id, :case_id, :document_id, :artifact_type, :display_name, :file_path,
                    :created_at, :mapping_revision_used, :artifact_status, :stale_reason,
                    :supersedes_artifact_id, :preview_snippet, :job_id, :mapping_path
                )
                """,
                asdict(record),
            )
            connection.commit()
        return record

    def list_by_case(self, case_id: str) -> list[ArtifactRecord]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM artifacts WHERE case_id = ? ORDER BY created_at DESC",
                (case_id,),
            ).fetchall()
        return [self._from_row(row) for row in rows]
