from __future__ import annotations

from dataclasses import asdict

from src.adapters.persistence.database import MetadataDatabase
from src.adapters.persistence.records import ReviewDecisionRecord


class ReviewDecisionRepository:
    def __init__(self, database: MetadataDatabase) -> None:
        self._database = database

    def create(self, record: ReviewDecisionRecord) -> ReviewDecisionRecord:
        with self._database.connect() as connection:
            connection.execute(
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
            connection.commit()
        return record
