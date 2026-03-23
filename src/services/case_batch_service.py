from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.adapters.documents.registry import DocumentAdapterRegistry
from src.adapters.mappings.canonical_mapping_adapter import CanonicalMappingAdapter
from src.adapters.persistence.artifact_repository import ArtifactRepository
from src.adapters.persistence.artifact_store import ArtifactStore
from src.adapters.persistence.case_repository import CaseRepository
from src.adapters.persistence.database import MetadataDatabase
from src.adapters.persistence.document_repository import DocumentRepository
from src.adapters.persistence.job_repository import JobRepository
from src.adapters.persistence.records import ArtifactRecord, CaseRecord, JobRecord
from src.services.anonymization_service import AnonymizationService
from src.services.mapping_revision_service import MappingRevisionService
from src.services.readiness_service import ReadinessService


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _snippet(text: str, *, limit: int = 80) -> str:
    compact = " ".join(text.split())
    return compact[:limit]


@dataclass(frozen=True)
class BatchProcessedItem:
    source_filename: str
    status: str
    output_path: str | None
    mapping_path: str | None
    error_summary: str | None
    mapping_revision: int | None


@dataclass(frozen=True)
class BatchExecutionResult:
    job: JobRecord
    items: tuple[BatchProcessedItem, ...]
    latest_revision: int | None
    progress_messages: tuple[str, ...]


class CaseBatchService:
    def __init__(
        self,
        *,
        database: MetadataDatabase,
        case_repository: CaseRepository,
        document_repository: DocumentRepository,
        job_repository: JobRepository,
        artifact_repository: ArtifactRepository,
        artifact_store: ArtifactStore,
        document_registry: DocumentAdapterRegistry,
        mapping_adapter: CanonicalMappingAdapter,
        mapping_revision_service: MappingRevisionService,
        anonymization_service: AnonymizationService,
        readiness_service: ReadinessService,
    ) -> None:
        self._database = database
        self._case_repository = case_repository
        self._document_repository = document_repository
        self._job_repository = job_repository
        self._artifact_repository = artifact_repository
        self._artifact_store = artifact_store
        self._document_registry = document_registry
        self._mapping_adapter = mapping_adapter
        self._mapping_revision_service = mapping_revision_service
        self._anonymization_service = anonymization_service
        self._readiness_service = readiness_service

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
            readiness_snapshot=str(
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

    @staticmethod
    def _cleanup_paths(*paths: Path | None) -> None:
        for path in paths:
            if path is not None and path.exists():
                path.unlink()

    def _process_document(
        self,
        *,
        case_record: CaseRecord,
        source_path: Path,
        job: JobRecord,
    ) -> BatchProcessedItem:
        adapter = self._document_registry.resolve_for_path(source_path)
        preview_text = adapter.load(source_path)
        source_fingerprint = self._artifact_store.fingerprint(source_path)
        imported_copy = self._artifact_store.import_copy(case_record.case_id, case_record.display_name, source_path)
        output_path = self._artifact_store.output_path(case_record.case_id, case_record.display_name, source_path, job.job_id)
        mapping_path = self._artifact_store.mapping_path(case_record.case_id, case_record.display_name, source_path, job.job_id)

        try:
            result = self._anonymization_service.run(
                backend="transformer",
                input_path=source_path,
                output_path=output_path,
                mapping_path=mapping_path,
            )
            incoming_artifact = self._mapping_adapter.load(mapping_path)
            with self._database.transaction() as connection:
                document_record = self._document_repository.create(
                    case_id=case_record.case_id,
                    source_path=source_path,
                    imported_copy_path=imported_copy,
                    source_fingerprint=source_fingerprint,
                    preview_snippet=_snippet(preview_text),
                    connection=connection,
                )
                merge_result, revision_record = self._mapping_revision_service.merge_incoming_artifact(
                    case_id=case_record.case_id,
                    incoming_artifact=incoming_artifact,
                    anonymized_text=result.result.anonymized_text,
                    change_reason=f"batch-import:{source_path.name}",
                    created_by_action="run_case_anonymization",
                    connection=connection,
                )
                adapter.save(result.output_path, merge_result.normalized_text)
                self._mapping_adapter.dump(merge_result.normalized_artifact, result.mapping_path)
                latest_revision = revision_record.revision_number if revision_record is not None else self._mapping_revision_service.latest_revision_number(case_record.case_id)
                artifact_record = self._artifact_repository.create(
                    ArtifactRecord(
                        artifact_id=uuid4().hex,
                        case_id=case_record.case_id,
                        document_id=document_record.document_id,
                        artifact_type="anonymized_text",
                        display_name=result.output_path.name,
                        file_path=str(result.output_path),
                        created_at=_utc_now(),
                        mapping_revision_used=latest_revision,
                        artifact_status="current",
                        stale_reason=None,
                        supersedes_artifact_id=None,
                        preview_snippet=_snippet(merge_result.normalized_text),
                        job_id=job.job_id,
                        mapping_path=str(result.mapping_path),
                        content_sha256=self._artifact_store.file_sha256(result.output_path),
                    ),
                    connection=connection,
                )
                self._document_repository.update_processing(
                    document_id=document_record.document_id,
                    document_status="success",
                    last_error_summary=None,
                    latest_output_artifact_id=artifact_record.artifact_id,
                    connection=connection,
                )
            return BatchProcessedItem(
                source_filename=source_path.name,
                status="success",
                output_path=str(result.output_path),
                mapping_path=str(result.mapping_path),
                error_summary=None,
                mapping_revision=latest_revision,
            )
        except Exception:
            self._cleanup_paths(output_path, mapping_path, imported_copy)
            raise

    def run_case_anonymization(self, case_record: CaseRecord, txt_file_paths: list[Path]) -> BatchExecutionResult:
        job = self._create_job(case_record.case_id, len(txt_file_paths))
        items: list[BatchProcessedItem] = []
        progress_messages: list[str] = []
        latest_revision = self._mapping_revision_service.latest_revision_number(case_record.case_id)

        for index, source_path in enumerate(txt_file_paths, start=1):
            try:
                item = self._process_document(
                    case_record=case_record,
                    source_path=source_path,
                    job=job,
                )
                items.append(item)
                latest_revision = item.mapping_revision if item.mapping_revision is not None else latest_revision
                job = replace(
                    job,
                    success_count=job.success_count + 1,
                    mapping_revision_used=latest_revision,
                )
                progress_messages.append(f"{index}/{len(txt_file_paths)} {source_path.name}: success")
            except Exception as exc:
                job = replace(job, failure_count=job.failure_count + 1, error_summary=str(exc))
                items.append(
                    BatchProcessedItem(
                        source_filename=source_path.name,
                        status="failed",
                        output_path=None,
                        mapping_path=None,
                        error_summary=str(exc),
                        mapping_revision=latest_revision,
                    )
                )
                progress_messages.append(f"{index}/{len(txt_file_paths)} {source_path.name}: failed")

        final_status = "success" if job.failure_count == 0 else ("partial" if job.success_count else "failed")
        case_status = "partial" if job.failure_count else "ready"
        with self._database.transaction() as connection:
            job = replace(
                job,
                completed_at=_utc_now(),
                job_status=final_status,
            )
            self._job_repository.update(job, connection=connection)
            self._case_repository.update_status(
                case_record.case_id,
                status_summary=case_status,
                connection=connection,
            )

        return BatchExecutionResult(
            job=job,
            items=tuple(items),
            latest_revision=latest_revision,
            progress_messages=tuple(progress_messages),
        )
