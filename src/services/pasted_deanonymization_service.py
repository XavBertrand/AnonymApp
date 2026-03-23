from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from dataclasses import replace
from pathlib import Path
import re
import shutil
from uuid import uuid4

from src.app.desktop.copy import fr
from src.adapters.documents.registry import DocumentAdapterRegistry
from src.adapters.persistence.artifact_repository import ArtifactRepository
from src.adapters.persistence.artifact_store import ArtifactStore
from src.adapters.persistence.case_repository import CaseRepository
from src.adapters.persistence.database import MetadataDatabase
from src.adapters.persistence.deanonymization_session_repository import DeanonymizationSessionRepository
from src.adapters.persistence.job_repository import JobRepository
from src.adapters.persistence.records import ArtifactRecord, DeanonymizationSessionRecord, JobRecord
from src.app.ui_contracts.case_workspace_view_models import DeanonymizationSessionViewModel
from src.models.mapping_artifact import MappingArtifact, MappingEntry, MappingOrigin
from src.services.deanonymization_service import DeanonymizationService
from src.services.mapping_revision_service import MappingRevisionService
from src.services.privacy_guard import PrivacyGuard
from src.services.readiness_service import ReadinessService


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass(frozen=True)
class DeanonymizationExportResult:
    artifact_id: str
    file_path: str
    session: DeanonymizationSessionViewModel


class PastedDeanonymizationService:
    _PLACEHOLDER_PATTERN = re.compile(r"<[^<>\r\n]+>")

    def __init__(
        self,
        *,
        database: MetadataDatabase,
        case_repository: CaseRepository,
        artifact_repository: ArtifactRepository,
        deanonymization_session_repository: DeanonymizationSessionRepository,
        job_repository: JobRepository,
        artifact_store: ArtifactStore,
        document_registry: DocumentAdapterRegistry,
        mapping_revision_service: MappingRevisionService,
        deanonymization_service: DeanonymizationService,
        readiness_service: ReadinessService,
    ) -> None:
        self._database = database
        self._case_repository = case_repository
        self._artifact_repository = artifact_repository
        self._deanonymization_session_repository = deanonymization_session_repository
        self._job_repository = job_repository
        self._artifact_store = artifact_store
        self._document_registry = document_registry
        self._mapping_revision_service = mapping_revision_service
        self._deanonymization_service = deanonymization_service
        self._readiness_service = readiness_service

    @staticmethod
    def _result_message(result_state: str, match_count: int) -> str:
        if result_state == "matched":
            return fr.DEANON_MATCHED_MESSAGE.format(match_count=match_count)
        if result_state == "partial":
            return fr.DEANON_PARTIAL_MESSAGE.format(match_count=match_count)
        if result_state == "no_match":
            return fr.DEANON_NO_MATCH_MESSAGE
        return fr.DEANON_FAILURE_MESSAGE

    @staticmethod
    def _classification_note(result_state: str) -> str | None:
        if result_state in {"partial", "no_match"}:
            return fr.DEANON_CLASSIFICATION_NOTE
        return None

    @staticmethod
    def _mapping_artifact_from_entries(active_entries: tuple) -> MappingArtifact:
        return MappingArtifact(
            schema_version="1.0",
            mapping_format="canonical-v1",
            origin=MappingOrigin(engine_id="transformer"),
            entries=[
                MappingEntry(
                    placeholder=entry.pseudonym,
                    original_value=entry.original_value,
                    entity_type=entry.entity_type,
                    position_ranges=[],
                )
                for entry in active_entries
            ],
        )

    def _match_count(self, input_text: str, mapping_artifact: MappingArtifact) -> int:
        placeholders = sorted({entry.placeholder for entry in mapping_artifact.entries if entry.placeholder}, key=len, reverse=True)
        if not placeholders:
            return 0
        pattern = re.compile("|".join(re.escape(item) for item in placeholders))
        return sum(1 for _ in pattern.finditer(input_text))

    def _result_state(self, input_text: str, match_count: int, mapping_artifact: MappingArtifact) -> str:
        if match_count == 0:
            return "no_match"
        known_placeholders = {entry.placeholder for entry in mapping_artifact.entries if entry.placeholder}
        placeholder_tokens = [match.group(0) for match in self._PLACEHOLDER_PATTERN.finditer(input_text)]
        if any(token not in known_placeholders for token in placeholder_tokens):
            return "partial"
        return "matched"

    @staticmethod
    def _session_view_model(
        record: DeanonymizationSessionRecord,
        *,
        input_text: str,
        result_text: str,
        exported_path: str | None = None,
    ) -> DeanonymizationSessionViewModel:
        return DeanonymizationSessionViewModel(
            session_id=record.session_id,
            case_id=record.case_id,
            input_text=input_text,
            result_text=result_text,
            match_count=record.match_count,
            result_state=record.session_status,
            mapping_revision=record.mapping_revision_used,
            status_message=PastedDeanonymizationService._result_message(record.session_status, record.match_count),
            classification_note=PastedDeanonymizationService._classification_note(record.session_status),
            exported_artifact_id=record.exported_artifact_id,
            exported_path=exported_path,
        )

    def _create_job(self, *, case_id: str, mapping_revision_used: int | None) -> JobRecord:
        return self._job_repository.create(
            JobRecord(
                job_id=uuid4().hex,
                case_id=case_id,
                job_type="pasted_deanonymization",
                started_at=_utc_now(),
                completed_at=None,
                job_status="running",
                mapping_revision_used=mapping_revision_used,
                item_count=1,
                success_count=0,
                failure_count=0,
                error_summary=None,
                readiness_snapshot=PrivacyGuard.readiness_snapshot(self._readiness_service.get_readiness_report()),
            )
        )

    def deanonymize(self, *, case_id: str, input_text: str) -> DeanonymizationSessionViewModel:
        case_record = self._case_repository.get(case_id)
        if case_record is None:
            raise ValueError(f"Unknown case '{case_id}'")
        if not input_text.strip():
            raise ValueError("Le texte anonymise a deanonymiser est requis.")

        mapping_revision, active_entries = self._mapping_revision_service.get_active_entries_with_revision(case_id)
        mapping_artifact = self._mapping_artifact_from_entries(active_entries)
        job = self._create_job(case_id=case_id, mapping_revision_used=mapping_revision)
        session_id = uuid4().hex
        input_path = self._artifact_store.deanonymization_input_path(case_id, case_record.display_name, session_id)
        result_path = self._artifact_store.deanonymization_result_path(case_id, case_record.display_name, session_id)
        adapter = self._document_registry.get("txt")
        try:
            adapter.save(input_path, input_text)
            result = self._deanonymization_service.run_text(
                input_text=input_text,
                mapping_artifact=mapping_artifact,
            )
            adapter.save(result_path, result.deanonymized_text)
            match_count = self._match_count(input_text, mapping_artifact)
            result_state = self._result_state(input_text, match_count, mapping_artifact)
            with self._database.transaction() as connection:
                record = self._deanonymization_session_repository.create(
                    DeanonymizationSessionRecord(
                        session_id=session_id,
                        case_id=case_id,
                        created_at=_utc_now(),
                        mapping_revision_used=mapping_revision,
                        input_text_path=str(input_path),
                        result_text_path=str(result_path),
                        input_preview_snippet=PrivacyGuard.preview_text(input_text),
                        result_preview_snippet=PrivacyGuard.preview_text(result.deanonymized_text),
                        match_count=match_count,
                        session_status=result_state,
                        exported_artifact_id=None,
                    ),
                    connection=connection,
                )
                self._job_repository.update(
                    replace(
                        job,
                        completed_at=_utc_now(),
                        job_status="partial" if result_state == "partial" else "success",
                        success_count=1,
                    ),
                    connection=connection,
                )
        except Exception as exc:
            if input_path.exists():
                input_path.unlink()
            if result_path.exists():
                result_path.unlink()
            self._job_repository.update(
                replace(
                    job,
                    completed_at=_utc_now(),
                    job_status="failed",
                    failure_count=1,
                    error_summary=str(exc),
                )
            )
            raise
        return self._session_view_model(
            record,
            input_text=input_text,
            result_text=result.deanonymized_text,
        )

    def export_result(
        self,
        *,
        case_id: str,
        session_id: str,
        destination: Path | None = None,
    ) -> DeanonymizationExportResult:
        case_record = self._case_repository.get(case_id)
        session = self._deanonymization_session_repository.get(session_id)
        if case_record is None or session is None or session.case_id != case_id:
            raise ValueError(f"Unknown deanonymization session '{session_id}' for case '{case_id}'")

        result_path = Path(session.result_text_path)
        if not result_path.exists():
            raise ValueError("La sortie deanonymisee est introuvable et ne peut pas etre exportee.")
        output_path = destination or self._artifact_store.deanonymized_export_path(case_id, case_record.display_name, session_id, uuid4().hex)
        if output_path.exists():
            raise ValueError("Le fichier d'export cible existe deja. Choisissez un nouveau chemin.")
        temp_output_path = output_path.with_name(f".{output_path.name}.{uuid4().hex}.tmp")
        adapter = self._document_registry.get("txt")
        result_text = result_path.read_text(encoding="utf-8")
        input_text = Path(session.input_text_path).read_text(encoding="utf-8") if Path(session.input_text_path).exists() else ""
        final_path_created = False
        previous_export = self._artifact_repository.get(session.exported_artifact_id) if session.exported_artifact_id is not None else None
        try:
            adapter.save(temp_output_path, result_text)
            with self._database.transaction() as connection:
                shutil.move(str(temp_output_path), str(output_path))
                final_path_created = True
                artifact = self._artifact_repository.create(
                    ArtifactRecord(
                        artifact_id=uuid4().hex,
                        case_id=case_id,
                        document_id=None,
                        artifact_type="deanonymized_export",
                        display_name=output_path.name,
                        file_path=str(output_path),
                        created_at=_utc_now(),
                        mapping_revision_used=session.mapping_revision_used,
                        artifact_status="current",
                        stale_reason=None,
                        supersedes_artifact_id=session.exported_artifact_id,
                        preview_snippet=PrivacyGuard.preview_text(result_text),
                        job_id=None,
                        mapping_path=None,
                        content_sha256=self._artifact_store.file_sha256(output_path),
                    ),
                    connection=connection,
                )
                if session.exported_artifact_id is not None:
                    self._artifact_repository.update_state(
                        artifact_id=session.exported_artifact_id,
                        artifact_status="superseded",
                        stale_reason=f"Remplace par l'export {artifact.artifact_id}",
                        supersedes_artifact_id=previous_export.supersedes_artifact_id if previous_export is not None else None,
                        connection=connection,
                    )
                self._deanonymization_session_repository.update_exported_artifact(
                    session_id=session_id,
                    exported_artifact_id=artifact.artifact_id,
                    connection=connection,
                )
        except Exception:
            if temp_output_path.exists():
                temp_output_path.unlink()
            if final_path_created and output_path.exists():
                output_path.unlink()
            raise

        updated_session = DeanonymizationSessionRecord(
            session_id=session.session_id,
            case_id=session.case_id,
            created_at=session.created_at,
            mapping_revision_used=session.mapping_revision_used,
            input_text_path=session.input_text_path,
            result_text_path=session.result_text_path,
            input_preview_snippet=session.input_preview_snippet,
            result_preview_snippet=session.result_preview_snippet,
            match_count=session.match_count,
            session_status=session.session_status,
            exported_artifact_id=artifact.artifact_id,
        )
        return DeanonymizationExportResult(
            artifact_id=artifact.artifact_id,
            file_path=str(output_path),
            session=self._session_view_model(
                updated_session,
                input_text=input_text,
                result_text=result_text,
                exported_path=str(output_path),
            ),
        )
