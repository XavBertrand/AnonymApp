from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import sqlite3
from uuid import uuid4

from src.adapters.persistence.database import MetadataDatabase
from src.adapters.persistence.records import CaseRecord


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CaseRepository:
    def __init__(self, database: MetadataDatabase) -> None:
        self._database = database

    @staticmethod
    def _from_row(row) -> CaseRecord:
        return CaseRecord(**dict(row))

    def create(self, display_name: str, *, connection: sqlite3.Connection | None = None) -> CaseRecord:
        now = _utc_now()
        record = CaseRecord(
            case_id=uuid4().hex,
            display_name=display_name,
            created_at=now,
            updated_at=now,
            last_opened_at=now,
            status_summary="ready",
            active_mapping_revision=None,
            deleted_at=None,
        )
        owns_connection = connection is None
        db_connection = connection or self._database.connect()
        try:
            db_connection.execute(
                """
                INSERT INTO cases (
                    case_id, display_name, created_at, updated_at, last_opened_at,
                    status_summary, active_mapping_revision, deleted_at
                ) VALUES (
                    :case_id, :display_name, :created_at, :updated_at, :last_opened_at,
                    :status_summary, :active_mapping_revision, :deleted_at
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

    def get(self, case_id: str) -> CaseRecord | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM cases WHERE case_id = ?",
                (case_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def list_active(self) -> list[CaseRecord]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM cases
                WHERE deleted_at IS NULL
                ORDER BY COALESCE(last_opened_at, created_at) DESC, created_at DESC
                """
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def set_last_opened(self, case_id: str) -> None:
        now = _utc_now()
        with self._database.connect() as connection:
            connection.execute(
                "UPDATE cases SET last_opened_at = ?, updated_at = ? WHERE case_id = ?",
                (now, now, case_id),
            )
            connection.commit()

    def update_status(
        self,
        case_id: str,
        *,
        status_summary: str,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        owns_connection = connection is None
        db_connection = connection or self._database.connect()
        try:
            db_connection.execute(
                """
                UPDATE cases
                SET status_summary = ?, updated_at = ?
                WHERE case_id = ?
                """,
                (status_summary, _utc_now(), case_id),
            )
            if owns_connection:
                db_connection.commit()
        finally:
            if owns_connection:
                db_connection.close()
