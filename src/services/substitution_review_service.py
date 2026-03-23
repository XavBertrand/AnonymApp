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
from src.adapters.persistence.records import ArtifactRecord, ReviewDecisionRecord
from src.adapters.persistence.review_decision_repository import ReviewDecisionRepository
from src.app.ui_contracts.case_workspace_view_models import SubstitutionReviewViewModel, SubstitutionRowViewModel
from src.models.mapping_artifact import MappingArtifact
from src.services.mapping_revision_service import MappingRevisionService
from src.services.mapping_rewrite_support import rewrite_artifact_for_removed_entries
from src.services.stale_state_service import StaleStateService


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _snippet(text: str, *, limit: int = 80) -> str:
    compact = " ".join(text.split())
    return compact[:limit]


class SubstitutionReviewService:
    def __init__(
        self,
        *,
        database: MetadataDatabase,
        case_repository: CaseRepository,
        document_repository: DocumentRepository,
        artifact_repository: ArtifactRepository,
        review_decision_repository: ReviewDecisionRepository,
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
        self._review_decision_repository = review_decision_repository
        self._artifact_store = artifact_store
        self._document_registry = document_registry
        self._mapping_revision_service = mapping_revision_service
        self._stale_state_service = stale_state_service
        self._mapping_adapter = mapping_adapter

    def _get_current_artifact(self, document_id: str) -> ArtifactRecord:
        document = self._document_repository.get(document_id)
        if document is None:
            raise ValueError(f"Unknown document '{document_id}'")
        if document.latest_output_artifact_id is None:
            raise ValueError(f"Document '{document_id}' has no generated output")
        artifact = self._artifact_repository.get(document.latest_output_artifact_id)
        if artifact is None:
            raise ValueError(f"Unknown artifact '{document.latest_output_artifact_id}'")
        return artifact

    def _build_rows(
        self,
        *,
        case_id: str,
        artifact_status: str,
        mapping_artifact: MappingArtifact | None,
    ) -> tuple[SubstitutionRowViewModel, ...]:
        if mapping_artifact is None:
            return ()
        current_entries = self._mapping_revision_service.get_entries(case_id)
        active_by_pair = {
            (entry.original_value, entry.pseudonym): entry
            for entry in current_entries
            if entry.state == "active"
        }
        removed_by_pair = {
            (entry.original_value, entry.pseudonym): entry
            for entry in current_entries
            if entry.state == "removed"
        }
        rows: list[SubstitutionRowViewModel] = []
        for entry in mapping_artifact.entries:
            revision_entry = active_by_pair.get((entry.original_value, entry.placeholder))
            unavailable_reason = None
            removable = revision_entry is not None and artifact_status == "current" and bool(entry.position_ranges)
            if artifact_status == "stale":
                unavailable_reason = "Regenerer la sortie obsolete avant de modifier cette substitution."
            elif artifact_status == "superseded":
                unavailable_reason = "Cette sortie historique ne peut plus etre modifiee."
            elif revision_entry is None and removed_by_pair.get((entry.original_value, entry.placeholder)) is not None:
                unavailable_reason = "Substitution deja retiree dans la revision courante."
            elif revision_entry is None:
                unavailable_reason = "Substitution indisponible dans la revision courante."
            elif not entry.position_ranges:
                unavailable_reason = "Positions fiables indisponibles pour cette substitution."
            rows.append(
                SubstitutionRowViewModel(
                    mapping_entry_id=revision_entry.mapping_entry_id if revision_entry is not None else "",
                    original_value=entry.original_value,
                    replacement_value=entry.placeholder,
                    entity_type=entry.entity_type,
                    removable=removable,
                    unavailable_reason=unavailable_reason,
                )
            )
        return tuple(rows)

    def load_review(self, *, case_id: str, document_id: str) -> SubstitutionReviewViewModel:
        case_record = self._case_repository.get(case_id)
        if case_record is None:
            raise ValueError(f"Unknown case '{case_id}'")
        document = self._document_repository.get(document_id)
        if document is None or document.case_id != case_id:
            raise ValueError(f"Unknown document '{document_id}' for case '{case_id}'")
        artifact = self._get_current_artifact(document_id)
        rewrite_base_state = self._stale_state_service.rewrite_base_trust_state(artifact)
        mapping_state = self._stale_state_service.load_mapping_artifact_state(
            artifact=artifact,
            mapping_loader=self._mapping_adapter.load,
        )
        displayed_status, safety_issue = self._stale_state_service.workspace_artifact_status(
            artifact=artifact,
            latest_revision=self._mapping_revision_service.latest_revision_number(case_id),
            output_missing=not self._stale_state_service.output_exists(artifact),
            rewrite_base_issue=rewrite_base_state.issue,
            mapping_issue=mapping_state.issue,
        )
        rows = self._build_rows(
            case_id=case_id,
            artifact_status=displayed_status,
            mapping_artifact=mapping_state.mapping_artifact,
        )
        editable, reason = self._stale_state_service.review_editability(
            artifact_status=displayed_status,
            rewrite_base_trusted=rewrite_base_state.trusted,
            rewrite_base_issue=rewrite_base_state.issue,
            mapping_issue=mapping_state.issue,
            has_removable_rows=any(row.removable for row in rows),
        )
        preview_text = Path(artifact.file_path).read_text(encoding="utf-8") if rewrite_base_state.trusted else artifact.preview_snippet
        return SubstitutionReviewViewModel(
            case_id=case_id,
            document_id=document_id,
            artifact_id=artifact.artifact_id,
            document_name=document.source_filename,
            artifact_status=displayed_status,
            mapping_revision=artifact.mapping_revision_used,
            preview_text=preview_text,
            stale_reason=safety_issue if displayed_status == "stale" else artifact.stale_reason,
            editable=editable,
            edit_unavailable_reason=reason,
            substitutions=rows,
        )

    def apply_removal(
        self,
        *,
        case_id: str,
        document_id: str,
        mapping_entry_ids: tuple[str, ...],
    ) -> tuple[str, tuple[str, ...]]:
        review = self.load_review(case_id=case_id, document_id=document_id)
        if not review.editable:
            raise ValueError(review.edit_unavailable_reason or "Substitution review is not editable")

        selected_ids = tuple(sorted(set(mapping_entry_ids)))
        if not selected_ids:
            raise ValueError("At least one substitution must be selected for removal")

        removable_ids = {row.mapping_entry_id for row in review.substitutions if row.removable}
        invalid_ids = sorted(set(selected_ids).difference(removable_ids))
        if invalid_ids:
            raise ValueError(f"Unknown or ineligible substitutions: {', '.join(invalid_ids)}")

        case_record = self._case_repository.get(case_id)
        document = self._document_repository.get(document_id)
        current_artifact = self._artifact_repository.get(review.artifact_id)
        if case_record is None or document is None or current_artifact is None:
            raise ValueError("Review context is no longer available")

        mapping_state = self._stale_state_service.load_mapping_artifact_state(
            artifact=current_artifact,
            mapping_loader=self._mapping_adapter.load,
        )
        if mapping_state.mapping_artifact is None:
            raise ValueError(mapping_state.issue or "Current review mapping artifact is unavailable")
        rewrite_base_state = self._stale_state_service.rewrite_base_trust_state(current_artifact)
        if not rewrite_base_state.trusted:
            raise ValueError(rewrite_base_state.issue or "Current review output is not trusted")
        current_text = Path(current_artifact.file_path).read_text(encoding="utf-8")

        active_entries = {
            entry.mapping_entry_id: entry
            for entry in self._mapping_revision_service.get_entries(case_id)
            if entry.state == "active"
        }
        removed_original_values = tuple(sorted({active_entries[item].original_value for item in selected_ids}))
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
            rewritten_text, rewritten_artifact = rewrite_artifact_for_removed_entries(
                text=current_text,
                mapping_artifact=mapping_state.mapping_artifact,
                removed_original_values=removed_original_values,
            )
            adapter = self._document_registry.resolve_for_path(output_path)
            adapter.save(output_path, rewritten_text)
            self._mapping_adapter.dump(rewritten_artifact, mapping_path)
            review_artifacts = tuple(self._artifact_repository.list_linked_for_review(case_id))
            with self._database.transaction() as connection:
                _, removed_entries, revision_record = self._mapping_revision_service.remove_entries(
                    case_id=case_id,
                    mapping_entry_ids=selected_ids,
                    change_reason=f"review-removal:{document.source_filename}",
                    created_by_action="remove_substitutions",
                    connection=connection,
                )
                removed_original_values = self._stale_state_service.removed_original_values(removed_entries)
                impacted_artifact_ids = self._stale_state_service.impacted_artifact_ids(
                    artifacts=review_artifacts,
                    removed_original_values=removed_original_values,
                    current_revision_number=revision_record.revision_number,
                    mapping_loader=self._mapping_adapter.load,
                )
                stale_reason = (
                    f"Revision {revision_record.revision_number}: "
                    f"substitutions retirees pour {', '.join(removed_original_values)}"
                )
                new_artifact = self._artifact_repository.create(
                    ArtifactRecord(
                        artifact_id=uuid4().hex,
                        case_id=case_id,
                        document_id=document_id,
                        artifact_type="anonymized_text",
                        display_name=output_path.name,
                        file_path=str(output_path),
                        created_at=_utc_now(),
                        mapping_revision_used=revision_record.revision_number,
                        artifact_status="current",
                        stale_reason=None,
                        supersedes_artifact_id=current_artifact.artifact_id,
                        preview_snippet=_snippet(rewritten_text),
                        job_id=None,
                        mapping_path=str(mapping_path),
                        content_sha256=self._artifact_store.file_sha256(output_path),
                    ),
                    connection=connection,
                )
                for mapping_entry_id in selected_ids:
                    self._review_decision_repository.create(
                        ReviewDecisionRecord(
                            review_decision_id=uuid4().hex,
                            case_id=case_id,
                            mapping_entry_id=mapping_entry_id,
                            decision_type="remove",
                            decided_at=_utc_now(),
                            applied_in_revision=revision_record.revision_number,
                            affected_artifact_count=len(impacted_artifact_ids),
                            decision_note=None,
                        ),
                        connection=connection,
                    )
                latest_output_lookup = {
                    item.latest_output_artifact_id: item
                    for item in self._document_repository.list_by_case(case_id)
                    if item.latest_output_artifact_id is not None
                }
                for artifact in review_artifacts:
                    if artifact.artifact_id not in impacted_artifact_ids:
                        continue
                    if artifact.artifact_id == current_artifact.artifact_id:
                        self._artifact_repository.update_state(
                            artifact_id=artifact.artifact_id,
                            artifact_status="superseded",
                            stale_reason=f"Remplace a la revision {revision_record.revision_number}",
                            supersedes_artifact_id=artifact.supersedes_artifact_id,
                            connection=connection,
                        )
                        continue
                    if artifact.artifact_status == "superseded":
                        continue
                    self._artifact_repository.update_state(
                        artifact_id=artifact.artifact_id,
                        artifact_status="stale",
                        stale_reason=stale_reason,
                        supersedes_artifact_id=artifact.supersedes_artifact_id,
                        connection=connection,
                    )
                    latest_document = latest_output_lookup.get(artifact.artifact_id)
                    if latest_document is not None:
                        self._document_repository.update_status(
                            document_id=latest_document.document_id,
                            document_status="stale",
                            last_error_summary=latest_document.last_error_summary,
                            latest_output_artifact_id=latest_document.latest_output_artifact_id,
                        connection=connection,
                    )
                self._document_repository.update_processing(
                    document_id=document_id,
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

        return document_id, impacted_artifact_ids
