from __future__ import annotations

from pathlib import Path

from src.app.desktop.presenters.workspace_presenter import WorkspacePresenter
from src.app.desktop.window import DesktopMainWindow
from tests.helpers.desktop_workspace_fakes import MappingPlanEntry, build_workspace_service


def test_desktop_window_create_case_and_run_batch(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"doc.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    presenter = WorkspacePresenter(service)
    window = DesktopMainWindow(presenter)
    window.load()

    input_path = tmp_path / "doc.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    window.create_case("Dossier UI")
    window.run_case_anonymization([input_path])

    assert window.current_case_id is not None
    assert window.case_workspace_panel.last_batch is not None
    assert Path(window.case_workspace_panel.last_batch.items[0].output_path).exists()
