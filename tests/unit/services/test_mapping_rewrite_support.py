from __future__ import annotations

from src.models.mapping_artifact import MappingArtifact, MappingEntry, MappingOrigin
from src.services.mapping_rewrite_support import TextRewrite, apply_text_rewrites, rewrite_artifact_for_removed_entries


def test_mapping_rewrite_support_preserves_shifted_ranges_consistently() -> None:
    text, artifact = rewrite_artifact_for_removed_entries(
        text="<PERSON_1> et <PERSON_2>",
        mapping_artifact=MappingArtifact(
            schema_version="1.0",
            mapping_format="canonical-v1",
            origin=MappingOrigin(engine_id="transformer"),
            entries=[
                MappingEntry(placeholder="<PERSON_1>", original_value="Alice", entity_type="PERSON", position_ranges=[(0, 10)]),
                MappingEntry(placeholder="<PERSON_2>", original_value="Bob", entity_type="PERSON", position_ranges=[(14, 24)]),
            ],
        ),
        removed_original_values=("Alice",),
    )

    assert text == "Alice et <PERSON_2>"
    assert artifact.entries[0].position_ranges == [(9, 19)]


def test_mapping_rewrite_support_applies_same_span_safe_rewrite_primitive_used_by_policy() -> None:
    assert apply_text_rewrites(
        "<PERSON_10> texte libre <PERSON_10>",
        (TextRewrite(start=0, end=11, replacement="<PERSON_1>"),),
    ) == "<PERSON_1> texte libre <PERSON_10>"
