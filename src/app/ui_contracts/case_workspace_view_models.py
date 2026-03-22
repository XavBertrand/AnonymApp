from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReadinessSummaryViewModel:
    state: str
    label: str
    details: tuple[str, ...] = ()


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
    display_name: str
    file_path: str
    status: str
    mapping_revision: int | None
    preview_snippet: str = ""


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
