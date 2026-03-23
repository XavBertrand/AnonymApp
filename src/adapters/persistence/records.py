from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CaseRecord:
    case_id: str
    display_name: str
    created_at: str
    updated_at: str
    last_opened_at: str | None
    status_summary: str
    active_mapping_revision: int | None
    deleted_at: str | None = None


@dataclass(frozen=True)
class DocumentRecord:
    document_id: str
    case_id: str
    source_filename: str
    source_display_path: str
    imported_copy_path: str | None
    source_fingerprint: str
    preview_snippet: str
    imported_at: str
    last_processed_at: str | None
    document_status: str
    last_error_summary: str | None
    latest_output_artifact_id: str | None


@dataclass(frozen=True)
class MappingRevisionRecord:
    case_id: str
    revision_number: int
    created_at: str
    change_reason: str
    base_revision_number: int | None
    entry_count: int
    conflict_resolution_strategy: str
    created_by_action: str
    entries_json: str


@dataclass(frozen=True)
class JobRecord:
    job_id: str
    case_id: str
    job_type: str
    started_at: str
    completed_at: str | None
    job_status: str
    mapping_revision_used: int | None
    item_count: int
    success_count: int
    failure_count: int
    error_summary: str | None
    readiness_snapshot: str | None


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_id: str
    case_id: str
    document_id: str | None
    artifact_type: str
    display_name: str
    file_path: str
    created_at: str
    mapping_revision_used: int | None
    artifact_status: str
    stale_reason: str | None
    supersedes_artifact_id: str | None
    preview_snippet: str
    job_id: str | None
    mapping_path: str | None
    content_sha256: str | None = None


@dataclass(frozen=True)
class DeanonymizationSessionRecord:
    session_id: str
    case_id: str
    created_at: str
    mapping_revision_used: int | None
    input_text_path: str
    result_text_path: str
    input_preview_snippet: str
    result_preview_snippet: str
    match_count: int
    session_status: str
    exported_artifact_id: str | None


@dataclass(frozen=True)
class ReviewDecisionRecord:
    review_decision_id: str
    case_id: str
    mapping_entry_id: str
    decision_type: str
    decided_at: str
    applied_in_revision: int
    affected_artifact_count: int
    decision_note: str | None
