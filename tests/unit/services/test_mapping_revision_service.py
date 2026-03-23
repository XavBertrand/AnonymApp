from __future__ import annotations

from src.adapters.persistence.case_repository import CaseRepository
from src.adapters.persistence.database import MetadataDatabase
from src.adapters.persistence.mapping_revision_repository import MappingRevisionRepository
from src.models.mapping_artifact import MappingArtifact, MappingEntry, MappingOrigin
from src.services.case_mapping_policy import CaseMappingPolicy
from src.services.mapping_revision_service import MappingRevisionService


def test_mapping_revision_service_tracks_removed_entries_and_blocks_reintroduction(tmp_path) -> None:
    database = MetadataDatabase(tmp_path / "desktop.sqlite3")
    database.bootstrap()
    case = CaseRepository(database).create("Dossier Revision")
    service = MappingRevisionService(
        MappingRevisionRepository(database),
        CaseMappingPolicy(),
    )

    first_merge, first_revision = service.merge_incoming_artifact(
        case_id=case.case_id,
        incoming_artifact=MappingArtifact(
            schema_version="1.0",
            mapping_format="canonical-v1",
            origin=MappingOrigin(engine_id="transformer"),
            entries=[
                MappingEntry(
                    placeholder="<PERSON_1>",
                    original_value="Alice",
                    entity_type="PERSON",
                    position_ranges=[(0, 10)],
                )
            ],
        ),
        anonymized_text="<PERSON_1> arrive",
        change_reason="batch-import:first.txt",
        created_by_action="run_case_anonymization",
    )

    assert first_revision is not None
    active_entry = first_merge.active_entries[0]

    updated_entries, removed_entries, removed_revision = service.remove_entries(
        case_id=case.case_id,
        mapping_entry_ids=(active_entry.mapping_entry_id,),
        change_reason="review-removal:first.txt",
        created_by_action="remove_substitutions",
    )

    assert removed_revision.revision_number == 2
    assert removed_entries[0].original_value == "Alice"
    assert removed_entries[0].state == "removed"
    assert all(entry.state == "removed" for entry in updated_entries)
    assert service.get_active_entries(case.case_id) == ()
    assert service.removed_entries_since(case_id=case.case_id, since_revision_number=1) == removed_entries

    second_merge, second_revision = service.merge_incoming_artifact(
        case_id=case.case_id,
        incoming_artifact=MappingArtifact(
            schema_version="1.0",
            mapping_format="canonical-v1",
            origin=MappingOrigin(engine_id="transformer"),
            entries=[
                MappingEntry(
                    placeholder="<PERSON_9>",
                    original_value="Alice",
                    entity_type="PERSON",
                    position_ranges=[(0, 10)],
                )
            ],
        ),
        anonymized_text="<PERSON_9> revient",
        change_reason="batch-import:second.txt",
        created_by_action="run_case_anonymization",
    )

    assert second_revision is None
    assert second_merge.normalized_text == "Alice revient"
    assert second_merge.normalized_artifact.entries == []
    assert service.latest_revision_number(case.case_id) == 2
