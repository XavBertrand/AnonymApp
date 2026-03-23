from __future__ import annotations

from pathlib import Path

from tests.helpers.desktop_workspace_fakes import MappingPlanEntry, build_workspace_service


def test_explicit_regeneration_refreshes_stale_output_only_when_requested(tmp_path: Path) -> None:
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

    workspace = service.create_case("Dossier Regen")
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

    regeneration = service.regenerate_stale_output(workspace.case_id, stale_artifact.artifact_id)

    assert regeneration.document_id == second_document.document_id
    assert regeneration.regenerated_artifact_id != stale_artifact.artifact_id
    assert regeneration.workspace.status_summary == "ready"
    regenerated_artifact = next(
        item for item in regeneration.workspace.artifacts if item.artifact_id == regeneration.regenerated_artifact_id
    )
    assert regenerated_artifact.status == "current"
    assert Path(regenerated_artifact.file_path).read_text(encoding="utf-8") == "Alice repart"
    assert all(item.status != "stale" for item in regeneration.workspace.artifacts)
