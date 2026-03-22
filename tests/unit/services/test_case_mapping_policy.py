from __future__ import annotations

from src.models.mapping_artifact import MappingArtifact, MappingEntry, MappingOrigin
from src.services.case_mapping_policy import ActiveMappingEntry, CaseMappingPolicy


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
