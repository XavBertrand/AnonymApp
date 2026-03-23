from __future__ import annotations

import json
from pathlib import Path

from tests.helpers.desktop_workspace_fakes import MappingPlanEntry, build_workspace_service


def test_reopened_stale_review_is_not_editable_until_output_is_regenerated(tmp_path: Path) -> None:
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

    workspace = service.create_case("Dossier Gating")
    batch = service.run_case_anonymization(workspace.case_id, [first, second])
    first_document = batch.workspace.documents[0]
    second_document = batch.workspace.documents[1]
    review = service.load_substitution_review(workspace.case_id, first_document.document_id)
    removable_id = next(row.mapping_entry_id for row in review.substitutions if row.removable)
    service.remove_substitutions(workspace.case_id, first_document.document_id, (removable_id,))

    stale_review = service.load_substitution_review(workspace.case_id, second_document.document_id)

    assert stale_review.artifact_status == "stale"
    assert stale_review.editable is False
    assert stale_review.edit_unavailable_reason is not None
    assert "obsolete" in stale_review.edit_unavailable_reason


def test_review_and_regeneration_are_gated_when_trusted_ranges_are_missing(tmp_path: Path) -> None:
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

    workspace = service.create_case("Dossier Trusted")
    batch = service.run_case_anonymization(workspace.case_id, [first, second])
    first_document = batch.workspace.documents[0]
    second_document = batch.workspace.documents[1]
    first_review = service.load_substitution_review(workspace.case_id, first_document.document_id)
    current_artifact = service._artifact_repository.get(first_review.artifact_id)
    current_mapping_path = Path(current_artifact.mapping_path)
    payload = json.loads(current_mapping_path.read_text(encoding="utf-8"))
    payload["entries"][0]["position_ranges"] = []
    current_mapping_path.write_text(json.dumps(payload), encoding="utf-8")

    blocked_review = service.load_substitution_review(workspace.case_id, first_document.document_id)

    assert blocked_review.editable is False
    assert blocked_review.substitutions[0].removable is False
    assert blocked_review.edit_unavailable_reason is not None
    assert "positions fiables" in blocked_review.edit_unavailable_reason

    current_mapping_path.write_text(json.dumps({
        **payload,
        "entries": [{**payload["entries"][0], "position_ranges": [[0, 10]]}],
    }), encoding="utf-8")
    repair_service = build_workspace_service(tmp_path)
    repaired_review = repair_service.load_substitution_review(workspace.case_id, first_document.document_id)
    removable_id = next(row.mapping_entry_id for row in repaired_review.substitutions if row.removable)
    repair_service.remove_substitutions(workspace.case_id, first_document.document_id, (removable_id,))

    reopened = build_workspace_service(tmp_path)
    stale_workspace = reopened.open_case(workspace.case_id)
    stale_artifact = next(
        item for item in stale_workspace.artifacts if item.document_id == second_document.document_id and item.status == "stale"
    )
    stale_record = reopened._artifact_repository.get(stale_artifact.artifact_id)
    stale_mapping_path = Path(stale_record.mapping_path)
    stale_payload = json.loads(stale_mapping_path.read_text(encoding="utf-8"))
    stale_payload["entries"][0]["position_ranges"] = []
    stale_mapping_path.write_text(json.dumps(stale_payload), encoding="utf-8")

    reopened_again = build_workspace_service(tmp_path)
    stale_workspace_again = reopened_again.open_case(workspace.case_id)
    blocked_artifact = next(
        item for item in stale_workspace_again.artifacts if item.document_id == second_document.document_id and item.status == "stale"
    )

    assert blocked_artifact.can_regenerate is False
    assert blocked_artifact.regeneration_unavailable_reason is not None
    assert "positions fiables" in blocked_artifact.regeneration_unavailable_reason
