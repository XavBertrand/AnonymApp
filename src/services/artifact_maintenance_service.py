from __future__ import annotations

from src.adapters.persistence.artifact_repository import ArtifactRepository
from src.adapters.persistence.artifact_store import ArtifactStore
from src.adapters.persistence.case_repository import CaseRepository
from src.adapters.persistence.database import MetadataDatabase


class ArtifactMaintenanceService:
    def __init__(
        self,
        *,
        database: MetadataDatabase,
        case_repository: CaseRepository,
        artifact_repository: ArtifactRepository,
        artifact_store: ArtifactStore,
    ) -> None:
        self._database = database
        self._case_repository = case_repository
        self._artifact_repository = artifact_repository
        self._artifact_store = artifact_store

    def reconcile_case(self, case_id: str) -> tuple[str, ...]:
        case_record = self._case_repository.get(case_id)
        if case_record is None:
            return ()
        missing = self._artifact_repository.list_missing_records(case_id)
        self._artifact_store.cleanup_case_temporary_files(case_id, case_record.display_name)
        if not missing:
            return ()
        with self._database.transaction() as connection:
            for record in missing:
                if record.artifact_status == "missing":
                    continue
                self._artifact_repository.update_state(
                    artifact_id=record.artifact_id,
                    artifact_status="missing",
                    stale_reason=record.stale_reason or "Le fichier suivi est introuvable sur disque.",
                    supersedes_artifact_id=record.supersedes_artifact_id,
                    connection=connection,
                )
        return tuple(record.artifact_id for record in missing)
