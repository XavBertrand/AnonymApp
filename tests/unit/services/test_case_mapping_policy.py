from __future__ import annotations

from src.models.mapping_artifact import MappingArtifact, MappingEntry, MappingOrigin
from src.services.case_mapping_policy import ActiveMappingEntry, CaseMappingPolicy, UnsafeSpanResolutionError


def test_case_mapping_policy_keeps_earliest_mapping_on_conflict() -> None:
    policy = CaseMappingPolicy()
    current = (
        ActiveMappingEntry(
            original_value="Alice",
            pseudonym="<PERSON_1>",
            entity_type="PERSON",
            introduced_in_revision=1,
        ),
    )
    incoming = MappingArtifact(
        schema_version="1.0",
        mapping_format="canonical-v1",
        origin=MappingOrigin(engine_id="transformer"),
        entries=[
            MappingEntry(
                placeholder="<PERSON_2>",
                original_value="Alice",
                entity_type="PERSON",
                position_ranges=[(0, 10)],
            )
        ],
    )

    merged = policy.merge(
        current_entries=current,
        incoming_artifact=incoming,
        anonymized_text="<PERSON_2> arrive",
        next_revision_number=2,
    )

    assert merged.normalized_text == "<PERSON_1> arrive"
    assert merged.normalized_artifact.entries[0].placeholder == "<PERSON_1>"
    assert merged.conflicts_resolved == 1
    assert merged.changed is False


def test_case_mapping_policy_is_deterministic_across_repeated_runs() -> None:
    policy = CaseMappingPolicy()
    current = ()
    incoming = MappingArtifact(
        schema_version="1.0",
        mapping_format="canonical-v1",
        origin=MappingOrigin(engine_id="transformer"),
        entries=[
            MappingEntry(
                placeholder="<PERSON_1>",
                original_value="Alice",
                entity_type="PERSON",
            )
        ],
    )

    first = policy.merge(
        current_entries=current,
        incoming_artifact=incoming,
        anonymized_text="<PERSON_1> arrive",
        next_revision_number=1,
    )
    second = policy.merge(
        current_entries=current,
        incoming_artifact=incoming,
        anonymized_text="<PERSON_1> arrive",
        next_revision_number=1,
    )

    assert first == second


def test_case_mapping_policy_rewrites_only_targeted_overlapping_placeholder_spans() -> None:
    policy = CaseMappingPolicy()
    current = (
        ActiveMappingEntry(
            original_value="Alice",
            pseudonym="<PERSON_1>",
            entity_type="PERSON",
            introduced_in_revision=1,
        ),
    )
    incoming = MappingArtifact(
        schema_version="1.0",
        mapping_format="canonical-v1",
        origin=MappingOrigin(engine_id="transformer"),
        entries=[
            MappingEntry(
                placeholder="<PERSON_10>",
                original_value="Alice",
                entity_type="PERSON",
                position_ranges=[(0, 11)],
            )
        ],
    )

    merged = policy.merge(
        current_entries=current,
        incoming_artifact=incoming,
        anonymized_text="<PERSON_10> <PERSON_10> literal <PERSON_10>",
        next_revision_number=2,
    )

    assert merged.normalized_text == "<PERSON_1> <PERSON_10> literal <PERSON_10>"
    assert merged.normalized_artifact.entries[0].position_ranges == [(0, 10)]


def test_case_mapping_policy_rewrites_repeated_tokens_without_substring_collisions() -> None:
    policy = CaseMappingPolicy()
    current = (
        ActiveMappingEntry(
            original_value="Alice",
            pseudonym="<PERSON_1>",
            entity_type="PERSON",
            introduced_in_revision=1,
        ),
    )
    incoming = MappingArtifact(
        schema_version="1.0",
        mapping_format="canonical-v1",
        origin=MappingOrigin(engine_id="transformer"),
        entries=[
            MappingEntry(
                placeholder="<PERSON_10>",
                original_value="Alice",
                entity_type="PERSON",
                position_ranges=[(0, 11), (22, 33)],
            )
        ],
    )

    merged = policy.merge(
        current_entries=current,
        incoming_artifact=incoming,
        anonymized_text="<PERSON_10> et encore <PERSON_10>",
        next_revision_number=2,
    )

    assert merged.normalized_text == "<PERSON_1> et encore <PERSON_1>"
    assert merged.conflicts_resolved == 2
    assert merged.normalized_artifact.entries[0].position_ranges == [(0, 10), (21, 31)]
    for start, end in merged.normalized_artifact.entries[0].position_ranges:
        assert merged.normalized_text[start:end] == merged.normalized_artifact.entries[0].placeholder


def test_case_mapping_policy_leaves_placeholder_like_literals_untouched_when_spans_are_trusted() -> None:
    policy = CaseMappingPolicy()
    current = (
        ActiveMappingEntry(
            original_value="Alice",
            pseudonym="<PERSON_1>",
            entity_type="PERSON",
            introduced_in_revision=1,
        ),
    )
    incoming = MappingArtifact(
        schema_version="1.0",
        mapping_format="canonical-v1",
        origin=MappingOrigin(engine_id="transformer"),
        entries=[
            MappingEntry(
                placeholder="<PERSON_10>",
                original_value="Alice",
                entity_type="PERSON",
                position_ranges=[(0, 11)],
            )
        ],
    )

    merged = policy.merge(
        current_entries=current,
        incoming_artifact=incoming,
        anonymized_text="<PERSON_10> texte libre <PERSON_10>",
        next_revision_number=2,
    )

    assert merged.normalized_text == "<PERSON_1> texte libre <PERSON_10>"
    assert merged.normalized_artifact.entries[0].position_ranges == [(0, 10)]


def test_case_mapping_policy_refuses_conflict_normalization_without_trusted_spans() -> None:
    policy = CaseMappingPolicy()
    current = (
        ActiveMappingEntry(
            original_value="Alice",
            pseudonym="<PERSON_1>",
            entity_type="PERSON",
            introduced_in_revision=1,
        ),
    )
    incoming = MappingArtifact(
        schema_version="1.0",
        mapping_format="canonical-v1",
        origin=MappingOrigin(engine_id="transformer"),
        entries=[
            MappingEntry(
                placeholder="<PERSON_10>",
                original_value="Alice",
                entity_type="PERSON",
                position_ranges=[],
            )
        ],
    )

    try:
        policy.merge(
            current_entries=current,
            incoming_artifact=incoming,
            anonymized_text="<PERSON_10> texte libre <PERSON_10>",
            next_revision_number=2,
        )
    except UnsafeSpanResolutionError as exc:
        assert "trusted spans" in str(exc)
    else:  # pragma: no cover - safety contract
        raise AssertionError("Expected unsafe span conflict to be rejected")
