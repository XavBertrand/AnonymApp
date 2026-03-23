from __future__ import annotations

from pathlib import Path

from tests.helpers.desktop_workspace_fakes import MappingPlanEntry, build_workspace_service


def test_removing_substitution_marks_other_impacted_outputs_stale(tmp_path: Path) -> None:
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

    workspace = service.create_case("Dossier Stale")
    batch = service.run_case_anonymization(workspace.case_id, [first, second])
    first_document = batch.workspace.documents[0]
    second_document = batch.workspace.documents[1]
    review = service.load_substitution_review(workspace.case_id, first_document.document_id)
    removable_id = next(row.mapping_entry_id for row in review.substitutions if row.removable)

    update = service.remove_substitutions(workspace.case_id, first_document.document_id, (removable_id,))

    assert update.workspace.status_summary == "stale"
    refreshed_second = next(item for item in update.workspace.documents if item.document_id == second_document.document_id)
    assert refreshed_second.latest_output_status == "stale"
    stale_artifact = next(
        item
        for item in update.workspace.artifacts
        if item.document_id == second_document.document_id and item.status == "stale"
    )
    assert stale_artifact.can_regenerate is True
    assert stale_artifact.stale_reason is not None
    assert "Alice" in stale_artifact.stale_reason
