from __future__ import annotations

import json
from dataclasses import asdict, replace
from datetime import datetime, timezone
import sqlite3

from src.adapters.persistence.mapping_revision_repository import MappingRevisionRepository
from src.adapters.persistence.records import MappingRevisionRecord
from src.models.mapping_artifact import MappingArtifact
from src.services.case_mapping_policy import (
    CaseMappingPolicy,
    MappingMergeResult,
    RevisionMappingEntry,
    make_mapping_entry_id,
)


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

    @staticmethod
    def _decode_entry(raw: dict) -> RevisionMappingEntry:
        introduced_in_revision = int(raw.get("introduced_in_revision", 1))
        original_value = str(raw["original_value"])
        pseudonym = str(raw["pseudonym"])
        entity_type = str(raw["entity_type"])
        return RevisionMappingEntry(
            mapping_entry_id=str(
                raw.get(
                    "mapping_entry_id",
                    make_mapping_entry_id(
                        original_value=original_value,
                        pseudonym=pseudonym,
                        entity_type=entity_type,
                        introduced_in_revision=introduced_in_revision,
                    ),
                )
            ),
            original_value=original_value,
            pseudonym=pseudonym,
            entity_type=entity_type,
            introduced_in_revision=introduced_in_revision,
            state=str(raw.get("state", "active")),
            removed_in_revision=raw.get("removed_in_revision"),
        )

    @staticmethod
    def _encode_entries(entries: tuple[RevisionMappingEntry, ...]) -> str:
        return json.dumps([asdict(entry) for entry in entries])

    def get_entries(self, case_id: str) -> tuple[RevisionMappingEntry, ...]:
        latest = self._repository.get_latest(case_id)
        if latest is None:
            return ()
        payload = json.loads(latest.entries_json)
        return tuple(self._decode_entry(item) for item in payload)

    def get_entries_for_revision(self, case_id: str, revision_number: int) -> tuple[RevisionMappingEntry, ...]:
        record = self._repository.get(case_id, revision_number)
        if record is None:
            return ()
        payload = json.loads(record.entries_json)
        return tuple(self._decode_entry(item) for item in payload)

    def get_active_entries(self, case_id: str) -> tuple[RevisionMappingEntry, ...]:
        return tuple(item for item in self.get_entries(case_id) if item.state == "active")

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
        connection: sqlite3.Connection | None = None,
    ) -> tuple[MappingMergeResult, MappingRevisionRecord | None]:
        latest = self._repository.get_latest(case_id)
        current_entries = self.get_entries(case_id)
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
            entries_json=self._encode_entries(merge_result.entries),
        )
        return merge_result, self._repository.create(record, connection=connection)

    def remove_entries(
        self,
        *,
        case_id: str,
        mapping_entry_ids: tuple[str, ...],
        change_reason: str,
        created_by_action: str,
        connection: sqlite3.Connection | None = None,
    ) -> tuple[tuple[RevisionMappingEntry, ...], tuple[RevisionMappingEntry, ...], MappingRevisionRecord]:
        latest = self._repository.get_latest(case_id)
        if latest is None:
            raise ValueError(f"Case '{case_id}' has no mapping revision to edit")

        current_entries = self.get_entries(case_id)
        if not mapping_entry_ids:
            raise ValueError("At least one mapping entry must be selected for removal")

        selected_ids = set(mapping_entry_ids)
        active_lookup = {
            entry.mapping_entry_id: entry
            for entry in current_entries
            if entry.state == "active"
        }
        missing = sorted(selected_ids.difference(active_lookup))
        if missing:
            raise ValueError(f"Unknown or inactive mapping entries: {', '.join(missing)}")

        next_revision_number = latest.revision_number + 1
        removed_entries: list[RevisionMappingEntry] = []
        updated_entries: list[RevisionMappingEntry] = []
        for entry in current_entries:
            if entry.mapping_entry_id not in selected_ids:
                updated_entries.append(entry)
                continue
            updated = replace(
                entry,
                state="removed",
                removed_in_revision=next_revision_number,
            )
            updated_entries.append(updated)
            removed_entries.append(updated)

        record = MappingRevisionRecord(
            case_id=case_id,
            revision_number=next_revision_number,
            created_at=_utc_now(),
            change_reason=change_reason,
            base_revision_number=latest.revision_number,
            entry_count=sum(1 for item in updated_entries if item.state == "active"),
            conflict_resolution_strategy="earliest-wins",
            created_by_action=created_by_action,
            entries_json=self._encode_entries(tuple(updated_entries)),
        )
        return (
            tuple(updated_entries),
            tuple(removed_entries),
            self._repository.create(record, connection=connection),
        )

    def removed_entries_since(
        self,
        *,
        case_id: str,
        since_revision_number: int | None,
        target_revision_number: int | None = None,
    ) -> tuple[RevisionMappingEntry, ...]:
        if target_revision_number is None:
            latest = self._repository.get_latest(case_id)
            if latest is None:
                return ()
            target_revision_number = latest.revision_number
        if since_revision_number is None or since_revision_number >= target_revision_number:
            return ()

        target_entries = self.get_entries_for_revision(case_id, target_revision_number)
        previous_entries = {
            entry.mapping_entry_id: entry
            for entry in self.get_entries_for_revision(case_id, since_revision_number)
        }
        removed: list[RevisionMappingEntry] = []
        for entry in target_entries:
            previous = previous_entries.get(entry.mapping_entry_id)
            if entry.state != "removed":
                continue
            if previous is None or previous.state != "removed":
                removed.append(entry)
        return tuple(
            sorted(
                removed,
                key=lambda item: (
                    item.removed_in_revision or 0,
                    item.original_value,
                    item.mapping_entry_id,
                ),
            )
        )
