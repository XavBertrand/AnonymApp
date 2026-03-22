from __future__ import annotations

from dataclasses import dataclass

from src.models.mapping_artifact import MappingArtifact, MappingEntry


@dataclass(frozen=True)
class ActiveMappingEntry:
    original_value: str
    pseudonym: str
    entity_type: str
    introduced_in_revision: int


@dataclass(frozen=True)
class MappingMergeResult:
    active_entries: tuple[ActiveMappingEntry, ...]
    normalized_artifact: MappingArtifact
    normalized_text: str
    conflicts_resolved: int
    changed: bool


class CaseMappingPolicy:
    def merge(
        self,
        *,
        current_entries: tuple[ActiveMappingEntry, ...],
        incoming_artifact: MappingArtifact,
        anonymized_text: str,
        next_revision_number: int,
    ) -> MappingMergeResult:
        active_by_original = {entry.original_value: entry for entry in current_entries}
        normalized_text = anonymized_text
        normalized_entries: list[MappingEntry] = []
        conflicts_resolved = 0
        changed = False

        for entry in incoming_artifact.entries:
            existing = active_by_original.get(entry.original_value)
            if existing is None:
                active_by_original[entry.original_value] = ActiveMappingEntry(
                    original_value=entry.original_value,
                    pseudonym=entry.placeholder,
                    entity_type=entry.entity_type,
                    introduced_in_revision=next_revision_number,
                )
                normalized_entries.append(entry)
                changed = True
                continue

            normalized_entries.append(
                MappingEntry(
                    placeholder=existing.pseudonym,
                    original_value=entry.original_value,
                    entity_type=entry.entity_type,
                    position_ranges=entry.position_ranges,
                )
            )
            if existing.pseudonym != entry.placeholder:
                normalized_text = normalized_text.replace(entry.placeholder, existing.pseudonym)
                conflicts_resolved += 1

        normalized_artifact = MappingArtifact(
            schema_version=incoming_artifact.schema_version,
            mapping_format=incoming_artifact.mapping_format,
            origin=incoming_artifact.origin,
            entries=normalized_entries,
            integrity_hash=incoming_artifact.integrity_hash,
        )
        normalized_artifact.validate()
        ordered_entries = tuple(sorted(active_by_original.values(), key=lambda item: (item.introduced_in_revision, item.original_value)))
        return MappingMergeResult(
            active_entries=ordered_entries,
            normalized_artifact=normalized_artifact,
            normalized_text=normalized_text,
            conflicts_resolved=conflicts_resolved,
            changed=changed,
        )
