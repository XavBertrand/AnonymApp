from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

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
from src.services.case_mapping_policy import CaseMappingPolicy
from src.services.mapping_revision_service import MappingRevisionService
from src.services.readiness_service import ReadinessService
from src.services.stale_state_service import StaleStateService


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _snippet(text: str, *, limit: int = 80) -> str:
    compact = " ".join(text.split())
    return compact[:limit]


class CaseWorkspaceService:
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
        self._anonymization_service = anonymization_service or AnonymizationService(document_adapter=TxtDocumentAdapter())
        self._case_mapping_policy = case_mapping_policy or CaseMappingPolicy()
        self._mapping_revision_service = mapping_revision_service or MappingRevisionService(
            mapping_repo,
            self._case_mapping_policy,
        )
        self._stale_state_service = stale_state_service or StaleStateService()

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

    def _to_case_list_item(self, record) -> CaseListItemViewModel:
        return CaseListItemViewModel(
            case_id=record.case_id,
            display_name=record.display_name,
            status_summary=record.status_summary,
            last_opened_at=record.last_opened_at,
        )

    def _to_workspace(self, case_id: str) -> CaseWorkspaceViewModel:
        case_record = self._case_repository.get(case_id)
        if case_record is None:
            raise ValueError(f"Unknown case '{case_id}'")
        documents = self._document_repository.list_by_case(case_id)
        artifacts = self._artifact_repository.list_by_case(case_id)
        return CaseWorkspaceViewModel(
            case_id=case_record.case_id,
            display_name=case_record.display_name,
            status_summary=case_record.status_summary,
            active_mapping_revision=case_record.active_mapping_revision,
            documents=tuple(
                DocumentItemViewModel(
                    document_id=item.document_id,
                    source_filename=item.source_filename,
                    status=item.document_status,
                    preview_snippet=item.preview_snippet,
                    latest_output_path=next((artifact.file_path for artifact in artifacts if artifact.artifact_id == item.latest_output_artifact_id), None),
                    error_summary=item.last_error_summary,
                )
                for item in documents
            ),
            artifacts=tuple(
                ArtifactItemViewModel(
                    artifact_id=item.artifact_id,
                    display_name=item.display_name,
                    file_path=item.file_path,
                    status=item.artifact_status,
                    mapping_revision=item.mapping_revision_used,
                )
                for item in artifacts
            ),
        )

    def load_workspace(self) -> WorkspaceLoadViewModel:
        cases = self._case_repository.list_active()
        selected = self._to_workspace(cases[0].case_id) if cases else None
        return WorkspaceLoadViewModel(
            readiness=self._readiness_summary(),
            cases=tuple(self._to_case_list_item(item) for item in cases),
            selected_case=selected,
        )

    def create_case(self, display_name: str) -> CaseWorkspaceViewModel:
        record = self._case_repository.create(display_name)
        self._artifact_store.ensure_case_dirs(record.case_id, record.display_name)
        return self._to_workspace(record.case_id)

    def open_case(self, case_id: str) -> CaseWorkspaceViewModel:
        self._case_repository.set_last_opened(case_id)
        return self._to_workspace(case_id)

    def _create_job(self, case_id: str, item_count: int) -> JobRecord:
        record = JobRecord(
            job_id=uuid4().hex,
            case_id=case_id,
            job_type="anonymization_batch",
            started_at=_utc_now(),
            completed_at=None,
            job_status="running",
            mapping_revision_used=self._mapping_revision_service.latest_revision_number(case_id),
            item_count=item_count,
            success_count=0,
            failure_count=0,
            error_summary=None,
            readiness_snapshot=json.dumps(
                [
                    {
                        "engine_id": item.engine_id,
                        "availability_status": item.availability_status,
                    }
                    for item in self._readiness_service.get_readiness_report()
                ]
            ),
        )
        return self._job_repository.create(record)

    def run_case_anonymization(self, case_id: str, txt_file_paths: list[Path]) -> BatchRunViewModel:
        case_record = self._case_repository.get(case_id)
        if case_record is None:
            raise ValueError(f"Unknown case '{case_id}'")
        job = self._create_job(case_id, len(txt_file_paths))
        items: list[BatchRunItemViewModel] = []
        progress_messages: list[str] = []
        latest_revision = self._mapping_revision_service.latest_revision_number(case_id)

        for index, source_path in enumerate(txt_file_paths, start=1):
            output_path = self._artifact_store.output_path(case_id, case_record.display_name, source_path, job.job_id)
            mapping_path = self._artifact_store.mapping_path(case_id, case_record.display_name, source_path, job.job_id)
            document_record = None
            try:
                adapter = self._document_registry.resolve_for_path(source_path)
                imported_copy = self._artifact_store.import_copy(case_id, case_record.display_name, source_path)
                preview_text = adapter.load(source_path)
                document_record = self._document_repository.create(
                    case_id=case_id,
                    source_path=source_path,
                    imported_copy_path=imported_copy,
                    source_fingerprint=self._artifact_store.fingerprint(source_path),
                    preview_snippet=_snippet(preview_text),
                )
                result = self._anonymization_service.run(
                    backend="transformer",
                    input_path=source_path,
                    output_path=output_path,
                    mapping_path=mapping_path,
                )
                artifact = self._mapping_adapter.load(mapping_path)
                merge_result, revision_record = self._mapping_revision_service.merge_incoming_artifact(
                    case_id=case_id,
                    incoming_artifact=artifact,
                    anonymized_text=result.result.anonymized_text,
                    change_reason=f"batch-import:{source_path.name}",
                    created_by_action="run_case_anonymization",
                )
                if revision_record is not None:
                    latest_revision = revision_record.revision_number
                normalized_output_path = result.output_path
                normalized_mapping_path = result.mapping_path
                adapter.save(normalized_output_path, merge_result.normalized_text)
                self._mapping_adapter.dump(merge_result.normalized_artifact, normalized_mapping_path)
                artifact_record = ArtifactRecord(
                    artifact_id=uuid4().hex,
                    case_id=case_id,
                    document_id=document_record.document_id,
                    artifact_type="anonymized_text",
                    display_name=normalized_output_path.name,
                    file_path=str(normalized_output_path),
                    created_at=_utc_now(),
                    mapping_revision_used=latest_revision,
                    artifact_status="current",
                    stale_reason=None,
                    supersedes_artifact_id=None,
                    preview_snippet=_snippet(merge_result.normalized_text),
                    job_id=job.job_id,
                    mapping_path=str(normalized_mapping_path),
                )
                artifact_record = self._artifact_repository.create(artifact_record)
                self._document_repository.update_processing(
                    document_id=document_record.document_id,
                    document_status="success",
                    last_error_summary=None,
                    latest_output_artifact_id=artifact_record.artifact_id,
                )
                job = replace(
                    job,
                    success_count=job.success_count + 1,
                    mapping_revision_used=latest_revision,
                )
                progress_messages.append(f"{index}/{len(txt_file_paths)} {source_path.name}: success")
                items.append(
                    BatchRunItemViewModel(
                        source_filename=source_path.name,
                        status="success",
                        output_path=str(normalized_output_path),
                        mapping_path=str(normalized_mapping_path),
                        error_summary=None,
                        mapping_revision=latest_revision,
                    )
                )
            except Exception as exc:
                if document_record is not None:
                    self._document_repository.update_processing(
                        document_id=document_record.document_id,
                        document_status="failed",
                        last_error_summary=str(exc),
                        latest_output_artifact_id=None,
                    )
                job = replace(job, failure_count=job.failure_count + 1, error_summary=str(exc))
                progress_messages.append(f"{index}/{len(txt_file_paths)} {source_path.name}: failed")
                items.append(
                    BatchRunItemViewModel(
                        source_filename=source_path.name,
                        status="failed",
                        output_path=None,
                        mapping_path=None,
                        error_summary=str(exc),
                        mapping_revision=latest_revision,
                    )
                )

        final_status = "success" if job.failure_count == 0 else ("partial" if job.success_count else "failed")
        job = replace(
            job,
            completed_at=_utc_now(),
            job_status=final_status,
        )
        self._job_repository.update(job)
        case_status = "partial" if job.failure_count else "ready"
        self._case_repository.update_status(case_id, status_summary=case_status, active_mapping_revision=latest_revision)
        workspace = self._to_workspace(case_id)
        return BatchRunViewModel(
            case_id=case_id,
            job_id=job.job_id,
            status=final_status,
            items=tuple(items),
            workspace=workspace,
            processed_count=job.success_count,
            failed_count=job.failure_count,
            progress_messages=tuple(progress_messages),
        )
