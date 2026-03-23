from __future__ import annotations

from dataclasses import dataclass

from src.models.mapping_artifact import MappingArtifact, MappingEntry


@dataclass(frozen=True)
class TextRewrite:
    start: int
    end: int
    replacement: str


def validate_rewrites(rewrites: tuple[TextRewrite, ...]) -> tuple[TextRewrite, ...]:
    ordered_rewrites = tuple(sorted(rewrites, key=lambda item: (item.start, item.end)))
    for previous, current in zip(ordered_rewrites, ordered_rewrites[1:]):
        if current.start < previous.end:
            raise ValueError("Overlapping rewrite ranges are not supported")
    return ordered_rewrites


def apply_text_rewrites(text: str, rewrites: tuple[TextRewrite, ...]) -> str:
    normalized = text
    for rewrite in sorted(rewrites, key=lambda item: item.start, reverse=True):
        normalized = f"{normalized[:rewrite.start]}{rewrite.replacement}{normalized[rewrite.end:]}"
    return normalized


def shift_range_for_rewrites(
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
            raise ValueError("Overlapping rewrite ranges are not supported")
    shifted_start = start + shift
    return shifted_start, shifted_start + replacement_length


def transform_mapping_entries_for_rewrites(
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
                    shift_range_for_rewrites(start=start, end=end, rewrites=rewrites)
                    for start, end in entry.position_ranges
                ],
            )
        )
    return transformed_entries


def rewrite_artifact_for_removed_entries(
    *,
    text: str,
    mapping_artifact: MappingArtifact,
    removed_original_values: tuple[str, ...],
) -> tuple[str, MappingArtifact]:
    removed = set(removed_original_values)
    rewrites: list[TextRewrite] = []
    retained_entries: list[MappingEntry] = []
    for entry in mapping_artifact.entries:
        if entry.original_value in removed:
            if not entry.position_ranges:
                raise ValueError("Trusted spans are required to remove a substitution safely")
            rewrites.extend(
                TextRewrite(start=start, end=end, replacement=entry.original_value)
                for start, end in entry.position_ranges
            )
            continue
        retained_entries.append(entry)

    ordered_rewrites = validate_rewrites(tuple(rewrites))
    rewritten_text = apply_text_rewrites(text, ordered_rewrites)
    transformed_entries = transform_mapping_entries_for_rewrites(
        entries=retained_entries,
        rewrites=ordered_rewrites,
    )
    rewritten_artifact = MappingArtifact(
        schema_version=mapping_artifact.schema_version,
        mapping_format=mapping_artifact.mapping_format,
        origin=mapping_artifact.origin,
        entries=transformed_entries,
        integrity_hash=mapping_artifact.integrity_hash,
    )
    rewritten_artifact.validate()
    return rewritten_text, rewritten_artifact
