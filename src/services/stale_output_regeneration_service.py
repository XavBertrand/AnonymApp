from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.adapters.documents.registry import DocumentAdapterRegistry
from src.adapters.persistence.artifact_repository import ArtifactRepository
from src.adapters.persistence.artifact_store import ArtifactStore
from src.adapters.persistence.case_repository import CaseRepository
from src.adapters.persistence.database import MetadataDatabase
from src.adapters.persistence.document_repository import DocumentRepository
from src.adapters.persistence.records import ArtifactRecord
from src.services.mapping_revision_service import MappingRevisionService
from src.services.mapping_rewrite_support import rewrite_artifact_for_removed_entries
from src.services.privacy_guard import PrivacyGuard
from src.services.stale_state_service import StaleStateService


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class StaleOutputRegenerationService:
    def __init__(
        self,
        *,
        database: MetadataDatabase,
        case_repository: CaseRepository,
        document_repository: DocumentRepository,
        artifact_repository: ArtifactRepository,
        artifact_store: ArtifactStore,
        document_registry: DocumentAdapterRegistry,
        mapping_revision_service: MappingRevisionService,
        stale_state_service: StaleStateService,
        mapping_adapter,
    ) -> None:
        self._database = database
        self._case_repository = case_repository
        self._document_repository = document_repository
        self._artifact_repository = artifact_repository
        self._artifact_store = artifact_store
        self._document_registry = document_registry
        self._mapping_revision_service = mapping_revision_service
        self._stale_state_service = stale_state_service
        self._mapping_adapter = mapping_adapter

    def regenerate(self, *, case_id: str, artifact_id: str) -> tuple[str, str]:
        case_record = self._case_repository.get(case_id)
        artifact = self._artifact_repository.get(artifact_id)
        if case_record is None or artifact is None or artifact.case_id != case_id:
            raise ValueError(f"Unknown artifact '{artifact_id}' for case '{case_id}'")
        if artifact.document_id is None:
            raise ValueError("Only document artifacts can be regenerated")

        document = self._document_repository.get(artifact.document_id)
        if document is None:
            raise ValueError(f"Unknown document '{artifact.document_id}'")

        mapping_state = self._stale_state_service.load_mapping_artifact_state(
            artifact=artifact,
            mapping_loader=self._mapping_adapter.load,
        )
        rewrite_base_state = self._stale_state_service.rewrite_base_trust_state(artifact)
        latest_revision = self._mapping_revision_service.latest_revision_number(case_id)
        removed_entries = self._mapping_revision_service.removed_entries_since(
            case_id=case_id,
            since_revision_number=artifact.mapping_revision_used,
            target_revision_number=latest_revision,
        )
        allowed, reason = self._stale_state_service.regeneration_eligibility(
            artifact_status=artifact.artifact_status,
            rewrite_base_trusted=rewrite_base_state.trusted,
            rewrite_base_issue=rewrite_base_state.issue,
            mapping_issue=mapping_state.issue,
            removed_entries=removed_entries,
            mapping_artifact=mapping_state.mapping_artifact,
            is_latest_for_document=document.latest_output_artifact_id == artifact.artifact_id,
        )
        if not allowed:
            raise ValueError(reason or "Stale output cannot be regenerated")
        if mapping_state.mapping_artifact is None or latest_revision is None:
            raise ValueError("Stale output cannot be regenerated")

        removed_original_values = self._stale_state_service.removed_original_values(removed_entries)
        action_id = uuid4().hex
        output_path = self._artifact_store.regenerated_output_path(
            case_record.case_id,
            case_record.display_name,
            document.source_filename,
            action_id,
        )
        mapping_path = self._artifact_store.regenerated_mapping_path(
            case_record.case_id,
            case_record.display_name,
            document.source_filename,
            action_id,
        )

        try:
            output_text = Path(artifact.file_path).read_text(encoding="utf-8")
            rewritten_text, rewritten_artifact = rewrite_artifact_for_removed_entries(
                text=output_text,
                mapping_artifact=mapping_state.mapping_artifact,
                removed_original_values=removed_original_values,
            )
            adapter = self._document_registry.resolve_for_path(output_path)
            adapter.save(output_path, rewritten_text)
            self._mapping_adapter.dump(rewritten_artifact, mapping_path)
            with self._database.transaction() as connection:
                new_artifact = self._artifact_repository.create(
                    ArtifactRecord(
                        artifact_id=uuid4().hex,
                        case_id=case_id,
                        document_id=document.document_id,
                        artifact_type=artifact.artifact_type,
                        display_name=output_path.name,
                        file_path=str(output_path),
                        created_at=_utc_now(),
                        mapping_revision_used=latest_revision,
                        artifact_status="current",
                        stale_reason=None,
                        supersedes_artifact_id=artifact.artifact_id,
                        preview_snippet=PrivacyGuard.preview_text(rewritten_text),
                        job_id=None,
                        mapping_path=str(mapping_path),
                        content_sha256=self._artifact_store.file_sha256(output_path),
                    ),
                    connection=connection,
                )
                self._artifact_repository.update_state(
                    artifact_id=artifact.artifact_id,
                    artifact_status="superseded",
                    stale_reason=f"Remplace a la revision {latest_revision}",
                    supersedes_artifact_id=artifact.supersedes_artifact_id,
                    connection=connection,
                )
                self._document_repository.update_processing(
                    document_id=document.document_id,
                    document_status="success",
                    last_error_summary=None,
                    latest_output_artifact_id=new_artifact.artifact_id,
                    connection=connection,
                )
        except Exception:
            if output_path.exists():
                output_path.unlink()
            if mapping_path.exists():
                mapping_path.unlink()
            raise

        return document.document_id, new_artifact.artifact_id
