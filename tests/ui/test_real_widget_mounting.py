from __future__ import annotations

from src.app.desktop.presenters.workspace_presenter import WorkspacePresenter
from src.app.desktop.qt_compat import QWidget
from src.app.desktop.window import DesktopMainWindow
from tests.helpers.desktop_workspace_fakes import build_workspace_service


def test_desktop_window_mounts_real_panel_widgets(tmp_path) -> None:
    window = DesktopMainWindow(WorkspacePresenter(build_workspace_service(tmp_path)))
    window.load()

    assert isinstance(window.case_history_panel, QWidget)
    assert isinstance(window.case_workspace_panel, QWidget)
    assert isinstance(window.mapping_review_panel, QWidget)
    assert isinstance(window.deanonymization_panel, QWidget)
    assert isinstance(window.readiness_panel, QWidget)
    assert isinstance(window.result_preview_panel, QWidget)


def test_desktop_window_exposes_interactive_controls_not_only_labels(tmp_path) -> None:
    window = DesktopMainWindow(WorkspacePresenter(build_workspace_service(tmp_path)))
    window.load()

    assert window.case_history_panel.create_case_button is not None
    assert window.case_history_panel.open_case_button is not None
    assert window.case_workspace_panel.run_button is not None
    assert window.mapping_review_panel.load_button is not None
    assert window.mapping_review_panel.remove_button is not None
    assert window.deanonymization_panel.run_button is not None
    assert window.deanonymization_panel.export_button is not None
    assert window.result_preview_panel.regenerate_button is not None
    assert window.readiness_panel.details_button is not None
