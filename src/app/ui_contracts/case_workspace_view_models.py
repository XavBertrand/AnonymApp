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


@dataclass(frozen=True)
class DocumentItemViewModel:
    document_id: str
    source_filename: str
    status: str
    preview_snippet: str
    latest_output_path: str | None = None
    error_summary: str | None = None


@dataclass(frozen=True)
class ArtifactItemViewModel:
    artifact_id: str
    display_name: str
    file_path: str
    status: str
    mapping_revision: int | None


@dataclass(frozen=True)
class CaseWorkspaceViewModel:
    case_id: str
    display_name: str
    status_summary: str
    active_mapping_revision: int | None
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
