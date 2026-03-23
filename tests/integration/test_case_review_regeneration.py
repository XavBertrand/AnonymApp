from __future__ import annotations

from pathlib import Path

from tests.helpers.desktop_workspace_fakes import MappingPlanEntry, build_workspace_service


def test_substitution_removal_creates_new_revision_and_regenerates_current_preview(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"piece.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    input_path = tmp_path / "piece.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    workspace = service.create_case("Dossier Review")
    batch = service.run_case_anonymization(workspace.case_id, [input_path])
    document_id = batch.workspace.documents[0].document_id

    review = service.load_substitution_review(workspace.case_id, document_id)
    removable_id = next(row.mapping_entry_id for row in review.substitutions if row.removable)

    update = service.remove_substitutions(workspace.case_id, document_id, (removable_id,))

    assert update.workspace.active_mapping_revision == 2
    assert update.review.preview_text == "Alice arrive"
    assert update.review.substitutions == ()
    assert update.workspace.documents[0].latest_output_status == "current"
    assert len(update.workspace.artifacts) == 2
    assert update.workspace.artifacts[0].status == "current"
    assert update.workspace.artifacts[1].status == "superseded"
    decisions = service._review_decision_repository.list_by_case(workspace.case_id)
    assert len(decisions) == 1
    assert decisions[0].mapping_entry_id == removable_id
