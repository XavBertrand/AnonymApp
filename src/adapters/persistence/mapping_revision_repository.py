from __future__ import annotations

from dataclasses import asdict

from src.adapters.persistence.database import MetadataDatabase
from src.adapters.persistence.records import MappingRevisionRecord


class MappingRevisionRepository:
    def __init__(self, database: MetadataDatabase) -> None:
        self._database = database

    @staticmethod
    def _from_row(row) -> MappingRevisionRecord:
        return MappingRevisionRecord(**dict(row))

    def create(self, record: MappingRevisionRecord) -> MappingRevisionRecord:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO mapping_revisions (
                    case_id, revision_number, created_at, change_reason, base_revision_number,
                    entry_count, conflict_resolution_strategy, created_by_action, entries_json
                ) VALUES (
                    :case_id, :revision_number, :created_at, :change_reason, :base_revision_number,
                    :entry_count, :conflict_resolution_strategy, :created_by_action, :entries_json
                )
                """,
                asdict(record),
            )
            connection.commit()
        return record

    def get_latest(self, case_id: str) -> MappingRevisionRecord | None:
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM mapping_revisions
                WHERE case_id = ?
                ORDER BY revision_number DESC
                LIMIT 1
                """,
                (case_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def list_by_case(self, case_id: str) -> list[MappingRevisionRecord]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM mapping_revisions
                WHERE case_id = ?
                ORDER BY revision_number ASC
                """,
                (case_id,),
            ).fetchall()
        return [self._from_row(row) for row in rows]
