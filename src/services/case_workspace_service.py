from __future__ import annotations

from pathlib import Path

from src.adapters.documents.registry import DocumentAdapterRegistry
from src.adapters.documents.txt_adapter import TxtDocumentAdapter
from src.adapters.mappings.canonical_mapping_adapter import CanonicalMappingAdapter
from src.adapters.persistence.artifact_repository import ArtifactRepository
from src.adapters.persistence.artifact_store import ArtifactStore
from src.adapters.persistence.case_repository import CaseRepository
from src.adapters.persistence.database import MetadataDatabase
from src.adapters.persistence.deanonymization_session_repository import DeanonymizationSessionRepository
from src.adapters.persistence.document_repository import DocumentRepository
from src.adapters.persistence.job_repository import JobRepository
from src.adapters.persistence.mapping_revision_repository import MappingRevisionRepository
from src.adapters.persistence.records import ArtifactRecord, JobRecord
from src.adapters.persistence.review_decision_repository import ReviewDecisionRepository
from src.app.ui_contracts.case_workspace_view_models import (
    ArtifactItemViewModel,
    BatchRunItemViewModel,
    BatchRunViewModel,
    CaseListItemViewModel,
    CaseWorkspaceViewModel,
    DocumentItemViewModel,
    ReadinessSummaryViewModel,
    WorkspaceLoadViewModel,
)
from src.services.anonymization_service import AnonymizationService
from src.services.case_batch_service import CaseBatchService
from src.services.case_mapping_policy import CaseMappingPolicy
from src.services.mapping_revision_service import MappingRevisionService
from src.services.readiness_service import ReadinessService
from src.services.stale_state_service import StaleStateService


class CaseDeletionBlockedError(RuntimeError):
    pass


class CaseWorkspaceService:
    DELETE_WHILE_RUNNING_MESSAGE = "Case deletion is unavailable while processing is in progress."

    def __init__(
        self,
        *,
        database: MetadataDatabase | None = None,
        case_repository: CaseRepository | None = None,
        document_repository: DocumentRepository | None = None,
        mapping_revision_repository: MappingRevisionRepository | None = None,
        job_repository: JobRepository | None = None,
        artifact_repository: ArtifactRepository | None = None,
        deanonymization_session_repository: DeanonymizationSessionRepository | None = None,
        review_decision_repository: ReviewDecisionRepository | None = None,
        artifact_store: ArtifactStore | None = None,
        document_registry: DocumentAdapterRegistry | None = None,
        mapping_adapter: CanonicalMappingAdapter | None = None,
        anonymization_service: AnonymizationService | None = None,
        readiness_service: ReadinessService | None = None,
        mapping_revision_service: MappingRevisionService | None = None,
        case_mapping_policy: CaseMappingPolicy | None = None,
        stale_state_service: StaleStateService | None = None,
    ) -> None:
        self._database = database or MetadataDatabase()
        self._database.bootstrap()
        self._case_repository = case_repository or CaseRepository(self._database)
        self._document_repository = document_repository or DocumentRepository(self._database)
        mapping_repo = mapping_revision_repository or MappingRevisionRepository(self._database)
        self._mapping_revision_repository = mapping_repo
        self._job_repository = job_repository or JobRepository(self._database)
        self._artifact_repository = artifact_repository or ArtifactRepository(self._database)
        self._deanonymization_session_repository = deanonymization_session_repository or DeanonymizationSessionRepository(self._database)
        self._review_decision_repository = review_decision_repository or ReviewDecisionRepository(self._database)
        self._artifact_store = artifact_store or ArtifactStore()
        self._document_registry = document_registry or DocumentAdapterRegistry([TxtDocumentAdapter()])
        self._mapping_adapter = mapping_adapter or CanonicalMappingAdapter()
        self._readiness_service = readiness_service or ReadinessService()
        self._anonymization_service = anonymization_service or AnonymizationService(
            document_registry=self._document_registry,
        )
        self._case_mapping_policy = case_mapping_policy or CaseMappingPolicy()
        self._mapping_revision_service = mapping_revision_service or MappingRevisionService(
            mapping_repo,
            self._case_mapping_policy,
        )
        self._stale_state_service = stale_state_service or StaleStateService()
        self._batch_service = CaseBatchService(
            database=self._database,
            case_repository=self._case_repository,
            document_repository=self._document_repository,
            job_repository=self._job_repository,
            artifact_repository=self._artifact_repository,
            artifact_store=self._artifact_store,
            document_registry=self._document_registry,
            mapping_adapter=self._mapping_adapter,
            mapping_revision_service=self._mapping_revision_service,
            anonymization_service=self._anonymization_service,
            readiness_service=self._readiness_service,
        )

    def _delete_availability(self, case_id: str, *, running_case_ids: set[str] | None = None) -> tuple[bool, str | None]:
        active_running_case_ids = running_case_ids if running_case_ids is not None else self._job_repository.running_case_ids()
        if case_id in active_running_case_ids:
            return False, self.DELETE_WHILE_RUNNING_MESSAGE
        return True, None

    def _build_workspace_load(self, preferred_case_id: str | None = None) -> WorkspaceLoadViewModel:
        cases = self._case_repository.list_active()
        running_case_ids = self._job_repository.running_case_ids()
        selected_case_id = preferred_case_id
        if selected_case_id is None and cases:
            selected_case_id = cases[0].case_id
        selected = self._to_workspace(selected_case_id, running_case_ids=running_case_ids) if selected_case_id is not None else None
        return WorkspaceLoadViewModel(
            readiness=self._readiness_summary(),
            cases=tuple(self._to_case_list_item(item, running_case_ids=running_case_ids) for item in cases),
            selected_case=selected,
        )

    def _readiness_summary(self) -> ReadinessSummaryViewModel:
        report = self._readiness_service.get_readiness_report()
        unavailable = [item.engine_id for item in report if item.availability_status == "unavailable"]
        if unavailable:
            return ReadinessSummaryViewModel(
                state="blocked",
                label="Bloque",
                details=tuple(unavailable),
            )
        return ReadinessSummaryViewModel(
            state="ready",
            label="Pret",
            details=tuple(item.engine_id for item in report),
        )

    def _to_case_list_item(self, record, *, running_case_ids: set[str] | None = None) -> CaseListItemViewModel:
        delete_available, delete_unavailable_reason = self._delete_availability(
            record.case_id,
            running_case_ids=running_case_ids,
        )
        return CaseListItemViewModel(
            case_id=record.case_id,
            display_name=record.display_name,
            status_summary=record.status_summary,
            last_opened_at=record.last_opened_at,
            delete_available=delete_available,
            delete_unavailable_reason=delete_unavailable_reason,
        )

    def _derive_case_status(
        self,
        *,
        stored_status: str,
        documents: tuple[DocumentItemViewModel, ...],
        artifacts: tuple[ArtifactItemViewModel, ...],
    ) -> str:
        if self._readiness_summary().state == "blocked":
            return "blocked"
        if any(item.status == "stale" for item in artifacts):
            return "stale"
        if any(item.status == "missing" for item in artifacts):
            return "partial"
        if any(item.status == "failed" for item in documents):
            return "partial"
        if stored_status in {"partial", "failed", "error", "blocked", "stale"}:
            return stored_status
        return "ready"

    def _to_workspace(self, case_id: str, *, running_case_ids: set[str] | None = None) -> CaseWorkspaceViewModel:
        case_record = self._case_repository.get(case_id)
        if case_record is None:
            raise ValueError(f"Unknown case '{case_id}'")
        documents = self._document_repository.list_by_case(case_id)
        artifacts = self._artifact_repository.list_by_case(case_id)
        missing_artifact_ids = self._artifact_repository.list_missing_ids(case_id)
        artifact_items = tuple(
            ArtifactItemViewModel(
                artifact_id=item.artifact_id,
                display_name=item.display_name,
                file_path=item.file_path,
                status="missing" if item.artifact_id in missing_artifact_ids else item.artifact_status,
                mapping_revision=item.mapping_revision_used,
                preview_snippet=item.preview_snippet,
            )
            for item in artifacts
        )
        artifact_lookup = {item.artifact_id: item for item in artifact_items}
        document_items = tuple(
            DocumentItemViewModel(
                document_id=item.document_id,
                source_filename=item.source_filename,
                status=item.document_status,
                preview_snippet=item.preview_snippet,
                source_display_path=item.source_display_path,
                latest_output_path=artifact_lookup[item.latest_output_artifact_id].file_path if item.latest_output_artifact_id in artifact_lookup else None,
                latest_output_status=artifact_lookup[item.latest_output_artifact_id].status if item.latest_output_artifact_id in artifact_lookup else None,
                error_summary=item.last_error_summary,
            )
            for item in documents
        )
        delete_available, delete_unavailable_reason = self._delete_availability(
            case_id,
            running_case_ids=running_case_ids,
        )
        return CaseWorkspaceViewModel(
            case_id=case_record.case_id,
            display_name=case_record.display_name,
            status_summary=self._derive_case_status(
                stored_status=case_record.status_summary,
                documents=document_items,
                artifacts=artifact_items,
            ),
            active_mapping_revision=self._mapping_revision_service.latest_revision_number(case_id),
            delete_available=delete_available,
            delete_unavailable_reason=delete_unavailable_reason,
            documents=document_items,
            artifacts=artifact_items,
        )

    def load_workspace(self) -> WorkspaceLoadViewModel:
        return self._build_workspace_load()

    def create_case(self, display_name: str) -> CaseWorkspaceViewModel:
        record = self._case_repository.create(display_name)
        self._artifact_store.ensure_case_dirs(record.case_id, record.display_name)
        return self._to_workspace(record.case_id)

    def open_case(self, case_id: str) -> CaseWorkspaceViewModel:
        self._case_repository.set_last_opened(case_id)
        return self._to_workspace(case_id)

    def delete_case(self, case_id: str, *, confirmed: bool) -> WorkspaceLoadViewModel:
        if not confirmed:
            raise ValueError("Case deletion requires explicit confirmation")
        case_record = self._case_repository.get(case_id)
        if case_record is None:
            raise ValueError(f"Unknown case '{case_id}'")
        if self._job_repository.has_running_job(case_id):
            raise CaseDeletionBlockedError(self.DELETE_WHILE_RUNNING_MESSAGE)
        self._case_repository.soft_delete(case_id)
        return self._build_workspace_load()

    def run_case_anonymization(self, case_id: str, txt_file_paths: list[Path]) -> BatchRunViewModel:
        case_record = self._case_repository.get(case_id)
        if case_record is None:
            raise ValueError(f"Unknown case '{case_id}'")
        batch_result = self._batch_service.run_case_anonymization(case_record, txt_file_paths)
        workspace = self._to_workspace(case_id)
        return BatchRunViewModel(
            case_id=case_id,
            job_id=batch_result.job.job_id,
            status=batch_result.job.job_status,
            items=tuple(
                BatchRunItemViewModel(
                    source_filename=item.source_filename,
                    status=item.status,
                    output_path=item.output_path,
                    mapping_path=item.mapping_path,
                    error_summary=item.error_summary,
                    mapping_revision=item.mapping_revision,
                )
                for item in batch_result.items
            ),
            workspace=workspace,
            processed_count=batch_result.job.success_count,
            failed_count=batch_result.job.failure_count,
            progress_messages=batch_result.progress_messages,
        )
