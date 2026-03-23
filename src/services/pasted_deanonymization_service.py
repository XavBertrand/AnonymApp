from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from uuid import uuid4

from src.adapters.documents.registry import DocumentAdapterRegistry
from src.adapters.persistence.artifact_repository import ArtifactRepository
from src.adapters.persistence.artifact_store import ArtifactStore
from src.adapters.persistence.case_repository import CaseRepository
from src.adapters.persistence.database import MetadataDatabase
from src.adapters.persistence.deanonymization_session_repository import DeanonymizationSessionRepository
from src.adapters.persistence.records import ArtifactRecord, DeanonymizationSessionRecord
from src.app.ui_contracts.case_workspace_view_models import DeanonymizationSessionViewModel
from src.models.mapping_artifact import MappingArtifact, MappingEntry, MappingOrigin
from src.services.deanonymization_service import DeanonymizationService
from src.services.mapping_revision_service import MappingRevisionService


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _snippet(text: str, *, limit: int = 80) -> str:
    compact = " ".join(text.split())
    return compact[:limit]


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
        artifact_store: ArtifactStore,
        document_registry: DocumentAdapterRegistry,
        mapping_revision_service: MappingRevisionService,
        deanonymization_service: DeanonymizationService,
    ) -> None:
        self._database = database
        self._case_repository = case_repository
        self._artifact_repository = artifact_repository
        self._deanonymization_session_repository = deanonymization_session_repository
        self._artifact_store = artifact_store
        self._document_registry = document_registry
        self._mapping_revision_service = mapping_revision_service
        self._deanonymization_service = deanonymization_service

    @staticmethod
    def _result_message(result_state: str, match_count: int) -> str:
        if result_state == "matched":
            return f"Deanonymisation terminee: {match_count} correspondance(s) restauree(s)."
        if result_state == "partial":
            return f"Deanonymisation partielle: {match_count} correspondance(s) restauree(s), certaines substitutions restent inconnues."
        if result_state == "no_match":
            return "Aucune correspondance connue n'a ete appliquee."
        return "La deanonymisation a echoue."

    def _active_mapping_artifact(self, case_id: str) -> MappingArtifact:
        active_entries = self._mapping_revision_service.get_active_entries(case_id)
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
        return sum(input_text.count(entry.placeholder) for entry in mapping_artifact.entries if entry.placeholder)

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
            exported_artifact_id=record.exported_artifact_id,
            exported_path=exported_path,
        )

    def deanonymize(self, *, case_id: str, input_text: str) -> DeanonymizationSessionViewModel:
        case_record = self._case_repository.get(case_id)
        if case_record is None:
            raise ValueError(f"Unknown case '{case_id}'")
        if not input_text.strip():
            raise ValueError("Le texte anonymise a deanonymiser est requis.")

        mapping_revision = self._mapping_revision_service.latest_revision_number(case_id)
        mapping_artifact = self._active_mapping_artifact(case_id)
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
            record = self._deanonymization_session_repository.create(
                DeanonymizationSessionRecord(
                    session_id=session_id,
                    case_id=case_id,
                    created_at=_utc_now(),
                    mapping_revision_used=mapping_revision,
                    input_text_path=str(input_path),
                    result_text_path=str(result_path),
                    input_preview_snippet=_snippet(input_text),
                    result_preview_snippet=_snippet(result.deanonymized_text),
                    match_count=match_count,
                    session_status=result_state,
                    exported_artifact_id=None,
                )
            )
        except Exception:
            if input_path.exists():
                input_path.unlink()
            if result_path.exists():
                result_path.unlink()
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
        output_path = destination or self._artifact_store.deanonymized_export_path(case_id, case_record.display_name, session_id)
        adapter = self._document_registry.get("txt")
        result_text = result_path.read_text(encoding="utf-8")
        input_text = Path(session.input_text_path).read_text(encoding="utf-8") if Path(session.input_text_path).exists() else ""
        try:
            adapter.save(output_path, result_text)
            with self._database.transaction() as connection:
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
                        preview_snippet=_snippet(result_text),
                        job_id=None,
                        mapping_path=None,
                        content_sha256=self._artifact_store.file_sha256(output_path),
                    ),
                    connection=connection,
                )
                self._deanonymization_session_repository.update_exported_artifact(
                    session_id=session_id,
                    exported_artifact_id=artifact.artifact_id,
                    connection=connection,
                )
        except Exception:
            if output_path.exists():
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
