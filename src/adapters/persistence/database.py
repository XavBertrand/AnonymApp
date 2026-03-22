from __future__ import annotations

import sqlite3
from pathlib import Path

from src.config.desktop_settings import DESKTOP_METADATA_DB, ensure_desktop_dirs


_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS cases (
        case_id TEXT PRIMARY KEY,
        display_name TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        last_opened_at TEXT,
        status_summary TEXT NOT NULL,
        active_mapping_revision INTEGER,
        deleted_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS documents (
        document_id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        source_filename TEXT NOT NULL,
        source_display_path TEXT NOT NULL,
        imported_copy_path TEXT,
        source_fingerprint TEXT NOT NULL,
        preview_snippet TEXT NOT NULL,
        imported_at TEXT NOT NULL,
        last_processed_at TEXT,
        document_status TEXT NOT NULL,
        last_error_summary TEXT,
        latest_output_artifact_id TEXT,
        FOREIGN KEY(case_id) REFERENCES cases(case_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mapping_revisions (
        case_id TEXT NOT NULL,
        revision_number INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        change_reason TEXT NOT NULL,
        base_revision_number INTEGER,
        entry_count INTEGER NOT NULL,
        conflict_resolution_strategy TEXT NOT NULL,
        created_by_action TEXT NOT NULL,
        entries_json TEXT NOT NULL,
        PRIMARY KEY (case_id, revision_number),
        FOREIGN KEY(case_id) REFERENCES cases(case_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS jobs (
        job_id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        job_type TEXT NOT NULL,
        started_at TEXT NOT NULL,
        completed_at TEXT,
        job_status TEXT NOT NULL,
        mapping_revision_used INTEGER,
        item_count INTEGER NOT NULL,
        success_count INTEGER NOT NULL,
        failure_count INTEGER NOT NULL,
        error_summary TEXT,
        readiness_snapshot TEXT,
        FOREIGN KEY(case_id) REFERENCES cases(case_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS artifacts (
        artifact_id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        document_id TEXT,
        artifact_type TEXT NOT NULL,
        display_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        created_at TEXT NOT NULL,
        mapping_revision_used INTEGER,
        artifact_status TEXT NOT NULL,
        stale_reason TEXT,
        supersedes_artifact_id TEXT,
        preview_snippet TEXT NOT NULL,
        job_id TEXT,
        mapping_path TEXT,
        FOREIGN KEY(case_id) REFERENCES cases(case_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS deanonymization_sessions (
        session_id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        mapping_revision_used INTEGER,
        input_preview_snippet TEXT NOT NULL,
        result_preview_snippet TEXT NOT NULL,
        match_count INTEGER NOT NULL,
        session_status TEXT NOT NULL,
        exported_artifact_id TEXT,
        FOREIGN KEY(case_id) REFERENCES cases(case_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS review_decisions (
        review_decision_id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        mapping_entry_id TEXT NOT NULL,
        decision_type TEXT NOT NULL,
        decided_at TEXT NOT NULL,
        applied_in_revision INTEGER NOT NULL,
        affected_artifact_count INTEGER NOT NULL,
        decision_note TEXT,
        FOREIGN KEY(case_id) REFERENCES cases(case_id)
    )
    """,
)


class MetadataDatabase:
    def __init__(self, path: Path | None = None) -> None:
        ensure_desktop_dirs()
        self.path = path or DESKTOP_METADATA_DB

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def bootstrap(self) -> None:
        with self.connect() as connection:
            for statement in _SCHEMA:
                connection.execute(statement)
            connection.commit()
