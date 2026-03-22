from __future__ import annotations

from dataclasses import asdict

from src.adapters.persistence.database import MetadataDatabase
from src.adapters.persistence.records import JobRecord


class JobRepository:
    def __init__(self, database: MetadataDatabase) -> None:
        self._database = database

    @staticmethod
    def _from_row(row) -> JobRecord:
        return JobRecord(**dict(row))

    def create(self, record: JobRecord) -> JobRecord:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    job_id, case_id, job_type, started_at, completed_at, job_status,
                    mapping_revision_used, item_count, success_count, failure_count,
                    error_summary, readiness_snapshot
                ) VALUES (
                    :job_id, :case_id, :job_type, :started_at, :completed_at, :job_status,
                    :mapping_revision_used, :item_count, :success_count, :failure_count,
                    :error_summary, :readiness_snapshot
                )
                """,
                asdict(record),
            )
            connection.commit()
        return record

    def update(self, record: JobRecord) -> JobRecord:
        with self._database.connect() as connection:
            connection.execute(
                """
                UPDATE jobs
                SET completed_at = :completed_at,
                    job_status = :job_status,
                    mapping_revision_used = :mapping_revision_used,
                    item_count = :item_count,
                    success_count = :success_count,
                    failure_count = :failure_count,
                    error_summary = :error_summary,
                    readiness_snapshot = :readiness_snapshot
                WHERE job_id = :job_id
                """,
                asdict(record),
            )
            connection.commit()
        return record

    def list_by_case(self, case_id: str) -> list[JobRecord]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM jobs WHERE case_id = ? ORDER BY started_at DESC",
                (case_id,),
            ).fetchall()
        return [self._from_row(row) for row in rows]
