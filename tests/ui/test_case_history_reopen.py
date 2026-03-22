from __future__ import annotations

from tests.helpers.desktop_workspace_fakes import build_workspace_service
from src.app.desktop.presenters.workspace_presenter import WorkspacePresenter
from src.app.desktop.window import DesktopMainWindow


def test_history_panel_reopens_case_and_refreshes_order(tmp_path) -> None:
    service = build_workspace_service(tmp_path)
    first = service.create_case("Dossier Un")
    second = service.create_case("Dossier Deux")

    presenter = WorkspacePresenter(service)
    window = DesktopMainWindow(presenter)
    window.load()

    assert window.case_history_panel.items[0].case_id == second.case_id

    window.case_history_panel.request_open_case(first.case_id)

    assert window.current_case_id == first.case_id
    assert window.case_history_panel.items[0].case_id == first.case_id
    assert window.case_workspace_panel.workspace is not None
    assert window.case_workspace_panel.workspace.case_id == first.case_id
