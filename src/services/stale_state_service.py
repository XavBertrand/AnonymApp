from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.adapters.persistence.artifact_store import ArtifactStore
from src.adapters.persistence.records import ArtifactRecord
from src.models.mapping_artifact import MappingArtifact
from src.services.case_mapping_policy import RevisionMappingEntry


@dataclass(frozen=True)
class MappingArtifactLoadState:
    mapping_artifact: MappingArtifact | None
    issue: str | None = None


@dataclass(frozen=True)
class RewriteBaseTrustState:
    trusted: bool
    issue: str | None = None


class StaleStateService:
    @staticmethod
    def uses_mapping_artifact(artifact: ArtifactRecord) -> bool:
        return artifact.document_id is not None and artifact.artifact_type == "anonymized_text"

    def removed_original_values(self, removed_entries: tuple[RevisionMappingEntry, ...]) -> tuple[str, ...]:
        return tuple(sorted({entry.original_value for entry in removed_entries}))

    def load_mapping_artifact_state(
        self,
        *,
        artifact: ArtifactRecord,
        mapping_loader,
    ) -> MappingArtifactLoadState:
        if not self.uses_mapping_artifact(artifact):
            return MappingArtifactLoadState(None, None)
        if artifact.mapping_path is None:
            return MappingArtifactLoadState(None, "Fichier de correspondance introuvable.")
        path = Path(artifact.mapping_path)
        if not path.exists():
            return MappingArtifactLoadState(None, "Fichier de correspondance introuvable.")
        try:
            mapping_artifact = mapping_loader(path)
        except Exception:
            return MappingArtifactLoadState(None, "Fichier de correspondance corrompu ou incompatible.")
        return MappingArtifactLoadState(mapping_artifact, None)

    def rewrite_base_trust_state(self, artifact: ArtifactRecord) -> RewriteBaseTrustState:
        output_path = Path(artifact.file_path)
        if not output_path.exists():
            return RewriteBaseTrustState(False, "Le fichier de sortie courant est introuvable.")
        if not artifact.content_sha256:
            return RewriteBaseTrustState(False, "L'integrite de la sortie ne peut pas etre verifiee.")
        current_sha = ArtifactStore.file_sha256(output_path)
        if current_sha != artifact.content_sha256:
            return RewriteBaseTrustState(False, "La sortie a ete modifiee hors de l'application et ne peut pas etre reutilisee.")
        return RewriteBaseTrustState(True, None)

    def impacted_artifact_ids(
        self,
        *,
        artifacts: tuple[ArtifactRecord, ...],
        removed_original_values: tuple[str, ...],
        current_revision_number: int | None,
        mapping_loader,
    ) -> tuple[str, ...]:
        if not removed_original_values:
            return ()
        removed = set(removed_original_values)
        impacted: list[str] = []
        for artifact in sorted(artifacts, key=lambda item: (item.created_at, item.artifact_id)):
            if artifact.document_id is None:
                continue
            mapping_state = self.load_mapping_artifact_state(
                artifact=artifact,
                mapping_loader=mapping_loader,
            )
            if mapping_state.mapping_artifact is None:
                if (
                    current_revision_number is not None
                    and artifact.mapping_revision_used is not None
                    and artifact.mapping_revision_used < current_revision_number
                ):
                    impacted.append(artifact.artifact_id)
                continue
            if any(entry.original_value in removed for entry in mapping_state.mapping_artifact.entries):
                impacted.append(artifact.artifact_id)
        return tuple(impacted)

    def review_editability(
        self,
        *,
        artifact_status: str,
        rewrite_base_trusted: bool,
        rewrite_base_issue: str | None,
        mapping_issue: str | None,
        has_removable_rows: bool,
    ) -> tuple[bool, str | None]:
        if artifact_status == "stale":
            return False, "Regenerer la sortie obsolete avant de modifier la revue."
        if artifact_status == "superseded":
            return False, "La sortie historique ne peut plus etre modifiee."
        if artifact_status == "missing":
            return False, "Le fichier de sortie courant est introuvable."
        if not rewrite_base_trusted:
            return False, rewrite_base_issue or "La sortie courante n'est pas fiable."
        if mapping_issue is not None:
            return False, mapping_issue
        if not has_removable_rows:
            return False, "Aucune substitution ne peut etre retiree sans positions fiables."
        return True, None

    def regeneration_eligibility(
        self,
        *,
        artifact_status: str,
        rewrite_base_trusted: bool,
        rewrite_base_issue: str | None,
        mapping_issue: str | None,
        removed_entries: tuple[RevisionMappingEntry, ...],
        mapping_artifact: MappingArtifact | None,
        is_latest_for_document: bool,
    ) -> tuple[bool, str | None]:
        if artifact_status != "stale":
            return False, "Seules les sorties obsoletes peuvent etre regenerees."
        if not is_latest_for_document:
            return False, "Seule la derniere sortie du document peut etre regeneree."
        if not rewrite_base_trusted:
            return False, rewrite_base_issue or "La sortie obsolete n'est pas fiable."
        if mapping_issue is not None or mapping_artifact is None:
            return False, mapping_issue or "Le fichier de correspondance de la sortie obsolete est introuvable."
        if not removed_entries:
            return False, "Aucune suppression de substitution n'affecte cette sortie."

        removed_by_original = {entry.original_value for entry in removed_entries}
        impacted_entries = [entry for entry in mapping_artifact.entries if entry.original_value in removed_by_original]
        if not impacted_entries:
            return False, "Aucune suppression de substitution n'affecte cette sortie."
        if any(not entry.position_ranges for entry in impacted_entries):
            return False, "Regeneration refusee: positions fiables indisponibles pour une substitution retiree."
        return True, None

    def workspace_artifact_status(
        self,
        *,
        artifact: ArtifactRecord,
        latest_revision: int | None,
        output_missing: bool,
        rewrite_base_issue: str | None,
        mapping_issue: str | None,
    ) -> tuple[str, str | None]:
        if output_missing:
            return "missing", rewrite_base_issue
        has_revision_lag = (
            latest_revision is not None
            and artifact.mapping_revision_used is not None
            and artifact.mapping_revision_used < latest_revision
        )
        if artifact.artifact_status == "stale" or (has_revision_lag and mapping_issue is not None):
            return "stale", mapping_issue or artifact.stale_reason
        if rewrite_base_issue is not None:
            return "unsafe", rewrite_base_issue
        if mapping_issue is not None and artifact.artifact_status not in {"superseded"}:
            return "unsafe", mapping_issue
        return artifact.artifact_status, artifact.stale_reason

    @staticmethod
    def output_exists(artifact: ArtifactRecord) -> bool:
        return Path(artifact.file_path).exists()
