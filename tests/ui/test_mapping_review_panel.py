from __future__ import annotations

from pathlib import Path

from src.app.desktop.qt_compat import process_events
from src.app.desktop.presenters.workspace_presenter import WorkspacePresenter
from src.app.desktop.window import DesktopMainWindow
from tests.helpers.desktop_workspace_fakes import MappingPlanEntry, build_workspace_service


def test_mapping_review_panel_supports_load_remove_and_explicit_regeneration(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={
            "first.txt": [MappingPlanEntry("Alice", "<PERSON_1>")],
            "second.txt": [MappingPlanEntry("Alice", "<PERSON_1>")],
        },
    )
    presenter = WorkspacePresenter(service)
    window = DesktopMainWindow(presenter)
    window.load()

    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("Alice arrive", encoding="utf-8")
    second.write_text("Alice repart", encoding="utf-8")

    window.create_case("Dossier UI Review")
    window.run_case_anonymization([first, second])
    window.pending_batch.result(timeout=2)
    process_events()

    current_workspace = window.case_workspace_panel.workspace
    assert current_workspace is not None
    first_document = current_workspace.documents[0]
    second_document = current_workspace.documents[1]

    window.mapping_review_panel.request_load_review(first_document.document_id)

    assert window.mapping_review_panel.review is not None
    removable_id = next(
        row.mapping_entry_id for row in window.mapping_review_panel.review.substitutions if row.removable
    )

    window.mapping_review_panel.request_remove_substitutions((removable_id,))

    assert window.mapping_review_panel.review is not None
    assert window.mapping_review_panel.review.preview_text == "Alice arrive"
    stale_artifact = next(
        item
        for item in window.result_preview_panel.artifacts
        if item.document_id == second_document.document_id and item.status == "stale"
    )
    assert stale_artifact.can_regenerate is True

    window.result_preview_panel.request_regenerate_artifact(stale_artifact.artifact_id)

    assert window.result_preview_panel.last_regeneration is not None
    regenerated_artifact = next(
        item
        for item in window.result_preview_panel.artifacts
        if item.document_id == second_document.document_id and item.status == "current"
    )
    assert Path(regenerated_artifact.file_path).read_text(encoding="utf-8") == "Alice repart"
