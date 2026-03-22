from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone

from src.adapters.persistence.mapping_revision_repository import MappingRevisionRepository
from src.adapters.persistence.records import MappingRevisionRecord
from src.models.mapping_artifact import MappingArtifact
from src.services.case_mapping_policy import ActiveMappingEntry, CaseMappingPolicy, MappingMergeResult


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MappingRevisionService:
    def __init__(
        self,
        repository: MappingRevisionRepository,
        policy: CaseMappingPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._policy = policy or CaseMappingPolicy()

    def get_active_entries(self, case_id: str) -> tuple[ActiveMappingEntry, ...]:
        latest = self._repository.get_latest(case_id)
        if latest is None:
            return ()
        payload = json.loads(latest.entries_json)
        return tuple(ActiveMappingEntry(**item) for item in payload)

    def latest_revision_number(self, case_id: str) -> int | None:
        latest = self._repository.get_latest(case_id)
        return latest.revision_number if latest else None

    def merge_incoming_artifact(
        self,
        *,
        case_id: str,
        incoming_artifact: MappingArtifact,
        anonymized_text: str,
        change_reason: str,
        created_by_action: str,
    ) -> tuple[MappingMergeResult, MappingRevisionRecord | None]:
        latest = self._repository.get_latest(case_id)
        current_entries = self.get_active_entries(case_id)
        next_revision_number = 1 if latest is None else latest.revision_number + 1
        merge_result = self._policy.merge(
            current_entries=current_entries,
            incoming_artifact=incoming_artifact,
            anonymized_text=anonymized_text,
            next_revision_number=next_revision_number,
        )
        if not merge_result.changed and latest is not None:
            return merge_result, None

        record = MappingRevisionRecord(
            case_id=case_id,
            revision_number=next_revision_number,
            created_at=_utc_now(),
            change_reason=change_reason,
            base_revision_number=latest.revision_number if latest else None,
            entry_count=len(merge_result.active_entries),
            conflict_resolution_strategy="earliest-wins",
            created_by_action=created_by_action,
            entries_json=json.dumps([asdict(entry) for entry in merge_result.active_entries]),
        )
        return merge_result, self._repository.create(record)
