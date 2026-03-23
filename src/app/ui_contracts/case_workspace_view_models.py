from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReadinessSummaryViewModel:
    state: str
    label: str
    message: str | None = None
    details: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReadinessCheckItemViewModel:
    check_name: str
    status: str
    severity: str
    message: str
    remediation: str | None = None


@dataclass(frozen=True)
class ReadinessBackendViewModel:
    engine_id: str
    display_name: str
    availability_status: str
    checks: tuple[ReadinessCheckItemViewModel, ...] = ()


@dataclass(frozen=True)
class ReadinessDetailsViewModel:
    state: str
    label: str
    message: str | None = None
    backends: tuple[ReadinessBackendViewModel, ...] = ()


@dataclass(frozen=True)
class CaseListItemViewModel:
    case_id: str
    display_name: str
    status_summary: str
    last_opened_at: str | None
    delete_available: bool = True
    delete_unavailable_reason: str | None = None


@dataclass(frozen=True)
class DocumentItemViewModel:
    document_id: str
    source_filename: str
    status: str
    preview_snippet: str
    source_display_path: str | None = None
    latest_output_path: str | None = None
    latest_output_status: str | None = None
    error_summary: str | None = None


@dataclass(frozen=True)
class ArtifactItemViewModel:
    artifact_id: str
    document_id: str | None
    display_name: str
    file_path: str
    status: str
    mapping_revision: int | None
    preview_snippet: str = ""
    stale_reason: str | None = None
    supersedes_artifact_id: str | None = None
    safety_issue: str | None = None
    can_regenerate: bool = False
    regeneration_unavailable_reason: str | None = None


@dataclass(frozen=True)
class CaseWorkspaceViewModel:
    case_id: str
    display_name: str
    status_summary: str
    active_mapping_revision: int | None
    delete_available: bool = True
    delete_unavailable_reason: str | None = None
    documents: tuple[DocumentItemViewModel, ...] = ()
    artifacts: tuple[ArtifactItemViewModel, ...] = ()


@dataclass(frozen=True)
class WorkspaceLoadViewModel:
    readiness: ReadinessSummaryViewModel
    cases: tuple[CaseListItemViewModel, ...]
    selected_case: CaseWorkspaceViewModel | None = None


@dataclass(frozen=True)
class BatchRunItemViewModel:
    source_filename: str
    status: str
    output_path: str | None = None
    mapping_path: str | None = None
    error_summary: str | None = None
    mapping_revision: int | None = None


@dataclass(frozen=True)
class BatchRunViewModel:
    case_id: str
    job_id: str
    status: str
    items: tuple[BatchRunItemViewModel, ...]
    workspace: CaseWorkspaceViewModel
    processed_count: int
    failed_count: int
    progress_messages: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SubstitutionRowViewModel:
    mapping_entry_id: str
    original_value: str
    replacement_value: str
    entity_type: str
    removable: bool
    unavailable_reason: str | None = None


@dataclass(frozen=True)
class SubstitutionReviewViewModel:
    case_id: str
    document_id: str
    artifact_id: str
    document_name: str
    artifact_status: str
    mapping_revision: int | None
    preview_text: str
    stale_reason: str | None = None
    editable: bool = False
    edit_unavailable_reason: str | None = None
    substitutions: tuple[SubstitutionRowViewModel, ...] = ()


@dataclass(frozen=True)
class ReviewUpdateViewModel:
    workspace: CaseWorkspaceViewModel
    review: SubstitutionReviewViewModel
    removed_mapping_entry_ids: tuple[str, ...]
    impacted_artifact_ids: tuple[str, ...]


@dataclass(frozen=True)
class StaleArtifactRegenerationViewModel:
    workspace: CaseWorkspaceViewModel
    artifact_id: str
    regenerated_artifact_id: str
    document_id: str
    review: SubstitutionReviewViewModel | None = None


@dataclass(frozen=True)
class DeanonymizationSessionViewModel:
    session_id: str
    case_id: str
    input_text: str
    result_text: str
    match_count: int
    result_state: str
    mapping_revision: int | None
    status_message: str
    classification_note: str | None = None
    exported_artifact_id: str | None = None
    exported_path: str | None = None


@dataclass(frozen=True)
class DeanonymizationExportViewModel:
    workspace: CaseWorkspaceViewModel
    session: DeanonymizationSessionViewModel
    artifact_id: str
    file_path: str
