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


@dataclass(frozen=True)
class TextRewrite:
    start: int
    end: int
    replacement: str


class UnsafeSpanResolutionError(ValueError):
    """Raised when deterministic normalization would require inferred rewrite spans."""


class CaseMappingPolicy:
    @staticmethod
    def _apply_rewrites(text: str, rewrites: tuple[TextRewrite, ...]) -> str:
        normalized = text
        for rewrite in sorted(rewrites, key=lambda item: item.start, reverse=True):
            normalized = f"{normalized[:rewrite.start]}{rewrite.replacement}{normalized[rewrite.end:]}"
        return normalized

    @staticmethod
    def _shift_for_range(
        *,
        start: int,
        end: int,
        rewrites: tuple[TextRewrite, ...],
    ) -> tuple[int, int]:
        shift = 0
        replacement_length = end - start
        for rewrite in rewrites:
            if rewrite.end <= start:
                shift += len(rewrite.replacement) - (rewrite.end - rewrite.start)
                continue
            if rewrite.start == start and rewrite.end == end:
                replacement_length = len(rewrite.replacement)
                continue
            if rewrite.start < end and rewrite.end > start:
                raise UnsafeSpanResolutionError("Overlapping placeholder rewrites are not supported")
        shifted_start = start + shift
        return shifted_start, shifted_start + replacement_length

    def _transform_ranges(
        self,
        *,
        entries: list[MappingEntry],
        rewrites: tuple[TextRewrite, ...],
    ) -> list[MappingEntry]:
        transformed_entries: list[MappingEntry] = []
        for entry in entries:
            if not entry.position_ranges:
                transformed_entries.append(
                    MappingEntry(
                        placeholder=entry.placeholder,
                        original_value=entry.original_value,
                        entity_type=entry.entity_type,
                        position_ranges=[],
                    )
                )
                continue

            transformed_entries.append(
                MappingEntry(
                    placeholder=entry.placeholder,
                    original_value=entry.original_value,
                    entity_type=entry.entity_type,
                    position_ranges=[
                        self._shift_for_range(start=start, end=end, rewrites=rewrites)
                        for start, end in entry.position_ranges
                    ],
                )
            )
        return transformed_entries

    def _build_rewrites(
        self,
        *,
        incoming_entries: list[MappingEntry],
        active_by_original: dict[str, ActiveMappingEntry],
        anonymized_text: str,
    ) -> tuple[TextRewrite, ...]:
        rewrites: list[TextRewrite] = []
        for entry in incoming_entries:
            existing = active_by_original.get(entry.original_value)
            if existing is None or existing.pseudonym == entry.placeholder:
                continue
            if not entry.position_ranges:
                raise UnsafeSpanResolutionError(
                    "Deterministic mapping conflict requires trusted spans; refusing to infer rewrite ranges"
                )
            ranges = entry.position_ranges
            rewrites.extend(
                TextRewrite(start=start, end=end, replacement=existing.pseudonym)
                for start, end in ranges
            )

        ordered = sorted(rewrites, key=lambda item: (item.start, item.end))
        for previous, current in zip(ordered, ordered[1:]):
            if current.start < previous.end:
                raise ValueError("Overlapping placeholder rewrites are not supported")
        return tuple(ordered)

    def merge(
        self,
        *,
        current_entries: tuple[ActiveMappingEntry, ...],
        incoming_artifact: MappingArtifact,
        anonymized_text: str,
        next_revision_number: int,
    ) -> MappingMergeResult:
        active_by_original = {entry.original_value: entry for entry in current_entries}
        normalized_entries: list[MappingEntry] = []
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
                normalized_entries.append(
                    MappingEntry(
                        placeholder=entry.placeholder,
                        original_value=entry.original_value,
                        entity_type=entry.entity_type,
                        position_ranges=entry.position_ranges,
                    )
                )
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

        rewrites = self._build_rewrites(
            incoming_entries=list(incoming_artifact.entries),
            active_by_original=active_by_original,
            anonymized_text=anonymized_text,
        )
        normalized_text = self._apply_rewrites(anonymized_text, rewrites)
        # Safety rule: once rewrites are applied, trusted positions are derived only by
        # transforming already-trusted spans. We never reconstruct spans by scanning text.
        normalized_entries = self._transform_ranges(entries=normalized_entries, rewrites=rewrites)

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
            conflicts_resolved=len(rewrites),
            changed=changed,
        )
