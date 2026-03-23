from __future__ import annotations

from dataclasses import asdict
import sqlite3

from src.adapters.persistence.database import MetadataDatabase
from src.adapters.persistence.records import ReviewDecisionRecord


class ReviewDecisionRepository:
    def __init__(self, database: MetadataDatabase) -> None:
        self._database = database

    def create(
        self,
        record: ReviewDecisionRecord,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> ReviewDecisionRecord:
        owns_connection = connection is None
        db_connection = connection or self._database.connect()
        try:
            db_connection.execute(
                """
                INSERT INTO review_decisions (
                    review_decision_id, case_id, mapping_entry_id, decision_type, decided_at,
                    applied_in_revision, affected_artifact_count, decision_note
                ) VALUES (
                    :review_decision_id, :case_id, :mapping_entry_id, :decision_type, :decided_at,
                    :applied_in_revision, :affected_artifact_count, :decision_note
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

    def list_by_case(self, case_id: str) -> list[ReviewDecisionRecord]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM review_decisions
                WHERE case_id = ?
                ORDER BY decided_at ASC, review_decision_id ASC
                """,
                (case_id,),
            ).fetchall()
        return [ReviewDecisionRecord(**dict(row)) for row in rows]
