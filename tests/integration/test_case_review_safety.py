from __future__ import annotations

from pathlib import Path
import pytest

from src.adapters.persistence.artifact_repository import ArtifactRepository
from src.adapters.persistence.database import MetadataDatabase
from tests.helpers.desktop_workspace_fakes import MappingPlanEntry, build_workspace_service


class FailingArtifactRepository(ArtifactRepository):
    def create(self, record, *, connection=None):
        raise RuntimeError("artifact write failed")


def test_workspace_reopen_survives_corrupt_mapping_and_marks_artifact_unsafe(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"piece.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    input_path = tmp_path / "piece.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    workspace = service.create_case("Dossier Unsafe")
    service.run_case_anonymization(workspace.case_id, [input_path])
    artifact = service._artifact_repository.list_by_case(workspace.case_id)[0]
    Path(artifact.mapping_path).write_text("{not-json", encoding="utf-8")

    reopened = build_workspace_service(tmp_path).open_case(workspace.case_id)

    assert reopened.artifacts[0].status == "unsafe"
    assert reopened.artifacts[0].safety_issue is not None
    assert reopened.artifacts[0].can_regenerate is False


def test_review_load_blocks_safely_when_mapping_file_is_corrupt(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"piece.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    input_path = tmp_path / "piece.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    workspace = service.create_case("Dossier Review Unsafe")
    batch = service.run_case_anonymization(workspace.case_id, [input_path])
    document_id = batch.workspace.documents[0].document_id
    artifact = service._artifact_repository.list_by_case(workspace.case_id)[0]
    Path(artifact.mapping_path).write_text("{not-json", encoding="utf-8")

    review = service.load_substitution_review(workspace.case_id, document_id)

    assert review.artifact_status == "unsafe"
    assert review.editable is False
    assert review.edit_unavailable_reason is not None
    assert "corrompu" in review.edit_unavailable_reason


def test_stale_regeneration_is_refused_safely_when_mapping_file_is_corrupt(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={
            "first.txt": [MappingPlanEntry("Alice", "<PERSON_1>")],
            "second.txt": [MappingPlanEntry("Alice", "<PERSON_1>")],
        },
    )
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("Alice arrive", encoding="utf-8")
    second.write_text("Alice repart", encoding="utf-8")

    workspace = service.create_case("Dossier Regen Unsafe")
    batch = service.run_case_anonymization(workspace.case_id, [first, second])
    first_document = batch.workspace.documents[0]
    second_document = batch.workspace.documents[1]
    review = service.load_substitution_review(workspace.case_id, first_document.document_id)
    removable_id = next(row.mapping_entry_id for row in review.substitutions if row.removable)
    update = service.remove_substitutions(workspace.case_id, first_document.document_id, (removable_id,))
    stale_artifact = next(
        item
        for item in update.workspace.artifacts
        if item.document_id == second_document.document_id and item.status == "stale"
    )
    stale_record = service._artifact_repository.get(stale_artifact.artifact_id)
    Path(stale_record.mapping_path).write_text("{not-json", encoding="utf-8")

    reopened = build_workspace_service(tmp_path)
    reopened_workspace = reopened.open_case(workspace.case_id)
    blocked_artifact = next(
        item for item in reopened_workspace.artifacts if item.document_id == second_document.document_id and item.status == "stale"
    )

    assert blocked_artifact.can_regenerate is False
    assert blocked_artifact.regeneration_unavailable_reason is not None
    with pytest.raises(ValueError, match="correspondance|corrompu"):
        reopened.regenerate_stale_output(workspace.case_id, blocked_artifact.artifact_id)


def test_missing_mapping_file_after_revision_change_never_remains_current(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={
            "first.txt": [MappingPlanEntry("Alice", "<PERSON_1>")],
            "second.txt": [MappingPlanEntry("Alice", "<PERSON_1>")],
        },
    )
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("Alice arrive", encoding="utf-8")
    second.write_text("Alice repart", encoding="utf-8")

    workspace = service.create_case("Dossier Missing Mapping")
    batch = service.run_case_anonymization(workspace.case_id, [first, second])
    first_document = batch.workspace.documents[0]
    second_document = batch.workspace.documents[1]
    review = service.load_substitution_review(workspace.case_id, first_document.document_id)
    removable_id = next(row.mapping_entry_id for row in review.substitutions if row.removable)

    second_latest = next(
        artifact for artifact in service._artifact_repository.list_by_case(workspace.case_id) if artifact.document_id == second_document.document_id
    )
    Path(second_latest.mapping_path).unlink()

    update = service.remove_substitutions(workspace.case_id, first_document.document_id, (removable_id,))

    refreshed_second = next(item for item in update.workspace.documents if item.document_id == second_document.document_id)
    assert refreshed_second.latest_output_status == "stale"


def test_externally_modified_current_output_blocks_review(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"piece.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    input_path = tmp_path / "piece.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    workspace = service.create_case("Dossier Tampered Review")
    batch = service.run_case_anonymization(workspace.case_id, [input_path])
    document_id = batch.workspace.documents[0].document_id
    artifact = service._artifact_repository.list_by_case(workspace.case_id)[0]
    Path(artifact.file_path).write_text("tampered", encoding="utf-8")

    blocked_review = service.load_substitution_review(workspace.case_id, document_id)

    assert blocked_review.artifact_status == "unsafe"
    assert blocked_review.editable is False
    assert blocked_review.edit_unavailable_reason is not None
    assert "modifiee" in blocked_review.edit_unavailable_reason


def test_externally_modified_stale_output_blocks_regeneration(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={
            "first.txt": [MappingPlanEntry("Alice", "<PERSON_1>")],
            "second.txt": [MappingPlanEntry("Alice", "<PERSON_1>")],
        },
    )
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("Alice arrive", encoding="utf-8")
    second.write_text("Alice repart", encoding="utf-8")

    workspace = service.create_case("Dossier Tampered Regen")
    batch = service.run_case_anonymization(workspace.case_id, [first, second])
    first_document = batch.workspace.documents[0]
    second_document = batch.workspace.documents[1]
    review = service.load_substitution_review(workspace.case_id, first_document.document_id)
    removable_id = next(row.mapping_entry_id for row in review.substitutions if row.removable)
    update = service.remove_substitutions(workspace.case_id, first_document.document_id, (removable_id,))
    stale_artifact = next(
        item
        for item in update.workspace.artifacts
        if item.document_id == second_document.document_id and item.status == "stale"
    )
    stale_record = service._artifact_repository.get(stale_artifact.artifact_id)
    Path(stale_record.file_path).write_text("tampered stale", encoding="utf-8")

    reopened = build_workspace_service(tmp_path)
    reopened_workspace = reopened.open_case(workspace.case_id)
    blocked_artifact = next(
        item for item in reopened_workspace.artifacts if item.document_id == second_document.document_id and item.status == "stale"
    )

    assert blocked_artifact.can_regenerate is False
    assert blocked_artifact.regeneration_unavailable_reason is not None
    assert "modifiee" in blocked_artifact.regeneration_unavailable_reason
    with pytest.raises(ValueError, match="modifiee"):
        reopened.regenerate_stale_output(workspace.case_id, blocked_artifact.artifact_id)


def test_review_failure_leaves_no_orphan_files(tmp_path: Path) -> None:
    database = MetadataDatabase(tmp_path / "desktop.sqlite3")
    service = build_workspace_service(
        tmp_path,
        database=database,
        plans_by_filename={"piece.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    input_path = tmp_path / "piece.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    workspace = service.create_case("Dossier Cleanup Review")
    batch = service.run_case_anonymization(workspace.case_id, [input_path])
    document_id = batch.workspace.documents[0].document_id
    review = service.load_substitution_review(workspace.case_id, document_id)
    removable_id = next(row.mapping_entry_id for row in review.substitutions if row.removable)
    before_outputs = set(service._artifact_store.case_root(workspace.case_id, workspace.display_name).glob("outputs/*"))
    before_mappings = set(service._artifact_store.case_root(workspace.case_id, workspace.display_name).glob("mappings/*"))

    failing = build_workspace_service(
        tmp_path,
        database=database,
        artifact_repository=FailingArtifactRepository(database),
    )
    with pytest.raises(RuntimeError, match="artifact write failed"):
        failing.remove_substitutions(workspace.case_id, document_id, (removable_id,))

    after_outputs = set(service._artifact_store.case_root(workspace.case_id, workspace.display_name).glob("outputs/*"))
    after_mappings = set(service._artifact_store.case_root(workspace.case_id, workspace.display_name).glob("mappings/*"))
    assert after_outputs == before_outputs
    assert after_mappings == before_mappings


def test_regeneration_failure_leaves_no_orphan_files(tmp_path: Path) -> None:
    database = MetadataDatabase(tmp_path / "desktop.sqlite3")
    service = build_workspace_service(
        tmp_path,
        database=database,
        plans_by_filename={
            "first.txt": [MappingPlanEntry("Alice", "<PERSON_1>")],
            "second.txt": [MappingPlanEntry("Alice", "<PERSON_1>")],
        },
    )
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("Alice arrive", encoding="utf-8")
    second.write_text("Alice repart", encoding="utf-8")

    workspace = service.create_case("Dossier Cleanup Regen")
    batch = service.run_case_anonymization(workspace.case_id, [first, second])
    first_document = batch.workspace.documents[0]
    second_document = batch.workspace.documents[1]
    review = service.load_substitution_review(workspace.case_id, first_document.document_id)
    removable_id = next(row.mapping_entry_id for row in review.substitutions if row.removable)
    update = service.remove_substitutions(workspace.case_id, first_document.document_id, (removable_id,))
    stale_artifact = next(
        item
        for item in update.workspace.artifacts
        if item.document_id == second_document.document_id and item.status == "stale"
    )
    case_root = service._artifact_store.case_root(workspace.case_id, workspace.display_name)
    before_outputs = set(case_root.glob("outputs/*"))
    before_mappings = set(case_root.glob("mappings/*"))

    failing = build_workspace_service(
        tmp_path,
        database=database,
        artifact_repository=FailingArtifactRepository(database),
    )
    with pytest.raises(RuntimeError, match="artifact write failed"):
        failing.regenerate_stale_output(workspace.case_id, stale_artifact.artifact_id)

    after_outputs = set(case_root.glob("outputs/*"))
    after_mappings = set(case_root.glob("mappings/*"))
    assert after_outputs == before_outputs
    assert after_mappings == before_mappings
