from __future__ import annotations

from pathlib import Path

from tests.helpers.desktop_workspace_fakes import MappingPlanEntry, build_workspace_service


def test_case_reopens_after_restart_with_documents_artifacts_and_snippets(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"piece.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    input_path = tmp_path / "piece.txt"
    input_path.write_text("Alice arrive au tribunal", encoding="utf-8")

    workspace = service.create_case("Dossier Reopen")
    service.run_case_anonymization(workspace.case_id, [input_path])

    restarted_service = build_workspace_service(tmp_path)
    load = restarted_service.load_workspace()
    reopened = restarted_service.open_case(workspace.case_id)

    assert any(item.case_id == workspace.case_id for item in load.cases)
    assert load.selected_case is not None
    assert reopened.case_id == workspace.case_id
    assert reopened.documents[0].source_filename == "piece.txt"
    assert reopened.documents[0].preview_snippet.startswith("Alice arrive")
    assert reopened.documents[0].latest_output_status == "current"
    assert reopened.artifacts[0].status == "current"
    assert reopened.artifacts[0].preview_snippet.startswith("<PERSON_1>")
