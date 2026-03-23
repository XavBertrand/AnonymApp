from __future__ import annotations

from pathlib import Path

from src.app.desktop.qt_compat import process_events
from src.app.desktop.presenters.workspace_presenter import WorkspacePresenter
from src.app.desktop.window import DesktopMainWindow
from tests.helpers.desktop_workspace_fakes import MappingPlanEntry, build_workspace_service


def test_deanonymization_panel_supports_pasted_text_and_export(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"piece.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    presenter = WorkspacePresenter(service)
    window = DesktopMainWindow(presenter)
    window.load()

    input_path = tmp_path / "piece.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    window.create_case("Dossier UI Deanon")
    window.run_case_anonymization([input_path])
    window.pending_batch.result(timeout=2)
    process_events()

    window.deanonymization_panel.set_input_text("<PERSON_1> arrive")
    window.deanonymization_panel.request_deanonymization()
    window.pending_deanonymization.result(timeout=2)
    process_events()

    assert window.deanonymization_panel.session is not None
    assert window.deanonymization_panel.session.result_text == "Alice arrive"
    assert window.deanonymization_panel.session.result_state == "matched"

    export_path = tmp_path / "custom-export.txt"
    window.deanonymization_panel.request_export(export_path)

    assert window.deanonymization_panel.last_export is not None
    assert export_path.read_text(encoding="utf-8") == "Alice arrive"
    exported_artifact = next(item for item in window.result_preview_panel.artifacts if item.file_path == str(export_path))
    assert exported_artifact.status == "current"
