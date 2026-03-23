from __future__ import annotations

from pathlib import Path

from src.app.desktop.qt_compat import process_events
from src.app.desktop.presenters.workspace_presenter import WorkspacePresenter
from src.app.desktop.window import DesktopMainWindow
from tests.helpers.desktop_workspace_fakes import MappingPlanEntry, build_workspace_service


def test_desktop_workspace_end_to_end_smoke(tmp_path: Path) -> None:
    plans = {
        "first.txt": [
            MappingPlanEntry("Alice", "<PERSON_1>"),
            MappingPlanEntry("Bob", "<PERSON_2>"),
        ],
        "second.txt": [MappingPlanEntry("Alice", "<PERSON_1>")],
    }
    service = build_workspace_service(tmp_path, plans_by_filename=plans)
    window = DesktopMainWindow(WorkspacePresenter(service))
    window.load()

    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("Alice rencontre Bob", encoding="utf-8")
    second.write_text("Alice repart", encoding="utf-8")

    window.create_case("Dossier Smoke")
    case_id = window.current_case_id
    assert case_id is not None

    window.run_case_anonymization([first, second])
    window.pending_batch.result(timeout=2)
    process_events()

    reopened = DesktopMainWindow(WorkspacePresenter(build_workspace_service(tmp_path, plans_by_filename=plans)))
    reopened.load()
    reopened.open_case(case_id)

    workspace = reopened.case_workspace_panel.workspace
    assert workspace is not None
    first_document = workspace.documents[0]
    second_document = workspace.documents[1]

    reopened.mapping_review_panel.request_load_review(first_document.document_id)
    review = reopened.mapping_review_panel.review
    assert review is not None
    removable_id = next(row.mapping_entry_id for row in review.substitutions if row.original_value == "Alice" and row.removable)
    reopened.mapping_review_panel.request_remove_substitutions((removable_id,))

    stale_artifact = next(
        item
        for item in reopened.result_preview_panel.artifacts
        if item.document_id == second_document.document_id and item.status == "stale"
    )
    reopened.result_preview_panel.request_regenerate_artifact(stale_artifact.artifact_id)

    current_review = reopened.mapping_review_panel.review
    assert current_review is not None
    assert "Alice" in current_review.preview_text

    reopened.deanonymization_panel.set_input_text("<PERSON_2> arrive")
    reopened.deanonymization_panel.request_deanonymization()
    reopened.pending_deanonymization.result(timeout=2)
    process_events()

    session = reopened.deanonymization_panel.session
    assert session is not None
    assert session.result_text == "Bob arrive"

    export_path = tmp_path / "smoke-export.txt"
    reopened.deanonymization_panel.request_export(export_path)

    assert export_path.exists()
    assert export_path.read_text(encoding="utf-8") == "Bob arrive"
    assert any(item.file_path == str(export_path) for item in reopened.result_preview_panel.artifacts)
