from __future__ import annotations

from pathlib import Path

from tests.helpers.desktop_workspace_fakes import MappingPlanEntry, build_workspace_service


def test_pasted_deanonymization_handles_known_and_unknown_matches(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"piece.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    input_path = tmp_path / "piece.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    workspace = service.create_case("Dossier Partiel")
    service.run_case_anonymization(workspace.case_id, [input_path])

    session = service.deanonymize_pasted_text(workspace.case_id, "<PERSON_1> parle a <PERSON_9>")

    assert session.result_text == "Alice parle a <PERSON_9>"
    assert session.result_state == "partial"
    assert session.match_count == 1
    assert "partielle" in session.status_message


def test_pasted_deanonymization_export_is_persisted_and_visible_in_workspace(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"piece.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    input_path = tmp_path / "piece.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    workspace = service.create_case("Dossier Export Visible")
    service.run_case_anonymization(workspace.case_id, [input_path])
    session = service.deanonymize_pasted_text(workspace.case_id, "<PERSON_1> arrive")

    export = service.export_deanonymized_result(workspace.case_id, session.session_id)
    reopened = service.open_case(workspace.case_id)

    assert Path(export.file_path).exists()
    exported_artifact = next(item for item in reopened.artifacts if item.artifact_id == export.artifact_id)
    assert exported_artifact.status == "current"
    assert exported_artifact.file_path == export.file_path
