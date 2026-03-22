from __future__ import annotations

from dataclasses import asdict
import sqlite3

from src.adapters.persistence.database import MetadataDatabase
from src.adapters.persistence.records import JobRecord


class JobRepository:
    def __init__(self, database: MetadataDatabase) -> None:
        self._database = database

    @staticmethod
    def _from_row(row) -> JobRecord:
        return JobRecord(**dict(row))

    def create(self, record: JobRecord, *, connection: sqlite3.Connection | None = None) -> JobRecord:
        owns_connection = connection is None
        db_connection = connection or self._database.connect()
        try:
            db_connection.execute(
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
            if owns_connection:
                db_connection.commit()
        finally:
            if owns_connection:
                db_connection.close()
        return record

    def update(self, record: JobRecord, *, connection: sqlite3.Connection | None = None) -> JobRecord:
        owns_connection = connection is None
        db_connection = connection or self._database.connect()
        try:
            db_connection.execute(
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
            if owns_connection:
                db_connection.commit()
        finally:
            if owns_connection:
                db_connection.close()
        return record

    def list_by_case(self, case_id: str) -> list[JobRecord]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM jobs WHERE case_id = ? ORDER BY started_at DESC",
                (case_id,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def has_running_job(self, case_id: str) -> bool:
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM jobs
                WHERE case_id = ? AND job_status = 'running'
                LIMIT 1
                """,
                (case_id,),
            ).fetchone()
        return row is not None

    def running_case_ids(self) -> set[str]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT case_id
                FROM jobs
                WHERE job_status = 'running'
                """
            ).fetchall()
        return {str(row["case_id"]) for row in rows}
