from __future__ import annotations

import hashlib
from dataclasses import dataclass

from src.models.mapping_artifact import MappingArtifact, MappingEntry
from src.services.mapping_rewrite_support import (
    TextRewrite,
    apply_text_rewrites,
    transform_mapping_entries_for_rewrites,
    validate_rewrites,
)


def make_mapping_entry_id(
    *,
    original_value: str,
    pseudonym: str,
    entity_type: str,
    introduced_in_revision: int,
) -> str:
    seed = "\0".join((original_value, pseudonym, entity_type, str(introduced_in_revision)))
    return f"map-{hashlib.sha1(seed.encode('utf-8')).hexdigest()[:16]}"


@dataclass(frozen=True)
class RevisionMappingEntry:
    mapping_entry_id: str
    original_value: str
    pseudonym: str
    entity_type: str
    introduced_in_revision: int
    state: str = "active"
    removed_in_revision: int | None = None


@dataclass(frozen=True)
class ActiveMappingEntry:
    original_value: str
    pseudonym: str
    entity_type: str
    introduced_in_revision: int

    @property
    def mapping_entry_id(self) -> str:
        return make_mapping_entry_id(
            original_value=self.original_value,
            pseudonym=self.pseudonym,
            entity_type=self.entity_type,
            introduced_in_revision=self.introduced_in_revision,
        )

    @property
    def state(self) -> str:
        return "active"

    @property
    def removed_in_revision(self) -> int | None:
        return None


@dataclass(frozen=True)
class MappingMergeResult:
    entries: tuple[RevisionMappingEntry, ...]
    normalized_artifact: MappingArtifact
    normalized_text: str
    conflicts_resolved: int
    changed: bool

    @property
    def active_entries(self) -> tuple[RevisionMappingEntry, ...]:
        return tuple(item for item in self.entries if item.state == "active")


class UnsafeSpanResolutionError(ValueError):
    """Raised when deterministic normalization would require inferred rewrite spans."""


class CaseMappingPolicy:
    def _build_rewrites(
        self,
        *,
        incoming_entries: list[MappingEntry],
        active_by_original: dict[str, RevisionMappingEntry],
        removed_by_original: dict[str, RevisionMappingEntry],
    ) -> tuple[TextRewrite, ...]:
        rewrites: list[TextRewrite] = []
        for entry in incoming_entries:
            removed = removed_by_original.get(entry.original_value)
            if removed is not None:
                if not entry.position_ranges:
                    raise UnsafeSpanResolutionError(
                        "Removed substitution requires trusted spans; refusing to infer rewrite ranges"
                    )
                rewrites.extend(
                    TextRewrite(start=start, end=end, replacement=entry.original_value)
                    for start, end in entry.position_ranges
                )
                continue

            existing = active_by_original.get(entry.original_value)
            if existing is None or existing.pseudonym == entry.placeholder:
                continue
            if not entry.position_ranges:
                raise UnsafeSpanResolutionError(
                    "Deterministic mapping conflict requires trusted spans; refusing to infer rewrite ranges"
                )
            rewrites.extend(
                TextRewrite(start=start, end=end, replacement=existing.pseudonym)
                for start, end in entry.position_ranges
            )
        try:
            return validate_rewrites(tuple(rewrites))
        except ValueError as exc:
            raise UnsafeSpanResolutionError(str(exc)) from exc

    def merge(
        self,
        *,
        current_entries: tuple[RevisionMappingEntry, ...],
        incoming_artifact: MappingArtifact,
        anonymized_text: str,
        next_revision_number: int,
    ) -> MappingMergeResult:
        active_by_original = {
            entry.original_value: entry
            for entry in current_entries
            if entry.state == "active"
        }
        removed_by_original = {
            entry.original_value: entry
            for entry in current_entries
            if entry.state == "removed"
        }
        normalized_entries: list[MappingEntry] = []
        new_entries: list[RevisionMappingEntry] = []

        for entry in incoming_artifact.entries:
            removed = removed_by_original.get(entry.original_value)
            if removed is not None:
                continue

            existing = active_by_original.get(entry.original_value)
            if existing is None:
                created = RevisionMappingEntry(
                    mapping_entry_id=make_mapping_entry_id(
                        original_value=entry.original_value,
                        pseudonym=entry.placeholder,
                        entity_type=entry.entity_type,
                        introduced_in_revision=next_revision_number,
                    ),
                    original_value=entry.original_value,
                    pseudonym=entry.placeholder,
                    entity_type=entry.entity_type,
                    introduced_in_revision=next_revision_number,
                )
                active_by_original[entry.original_value] = created
                new_entries.append(created)
                normalized_entries.append(
                    MappingEntry(
                        placeholder=entry.placeholder,
                        original_value=entry.original_value,
                        entity_type=entry.entity_type,
                        position_ranges=entry.position_ranges,
                    )
                )
                continue

            normalized_entries.append(
                MappingEntry(
                    placeholder=existing.pseudonym,
                    original_value=entry.original_value,
                    entity_type=entry.entity_type,
                    position_ranges=entry.position_ranges,
                )
            )

        rewrites = self._build_rewrites(
            incoming_entries=list(incoming_artifact.entries),
            active_by_original=active_by_original,
            removed_by_original=removed_by_original,
        )
        normalized_text = apply_text_rewrites(anonymized_text, rewrites)
        try:
            normalized_entries = transform_mapping_entries_for_rewrites(entries=normalized_entries, rewrites=rewrites)
        except ValueError as exc:
            raise UnsafeSpanResolutionError(str(exc)) from exc

        normalized_artifact = MappingArtifact(
            schema_version=incoming_artifact.schema_version,
            mapping_format=incoming_artifact.mapping_format,
            origin=incoming_artifact.origin,
            entries=normalized_entries,
            integrity_hash=incoming_artifact.integrity_hash,
        )
        normalized_artifact.validate()
        ordered_entries = tuple(
            sorted(
                (*current_entries, *new_entries),
                key=lambda item: (
                    item.introduced_in_revision,
                    item.original_value,
                    item.pseudonym,
                    item.mapping_entry_id,
                ),
            )
        )
        return MappingMergeResult(
            entries=ordered_entries,
            normalized_artifact=normalized_artifact,
            normalized_text=normalized_text,
            conflicts_resolved=len(rewrites),
            changed=bool(new_entries),
        )
