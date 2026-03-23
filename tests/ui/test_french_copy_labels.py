from __future__ import annotations

from src.app.desktop.copy import fr
from src.app.desktop.presenters.workspace_presenter import WorkspacePresenter
from src.app.desktop.window import DesktopMainWindow
from tests.helpers.desktop_workspace_fakes import build_workspace_service


def test_french_copy_inventory_is_used_for_window_and_core_messages(tmp_path) -> None:
    service = build_workspace_service(tmp_path)
    window = DesktopMainWindow(WorkspacePresenter(service))
    window.load()

    assert getattr(window, "window_title", None) == fr.APP_TITLE or window.windowTitle() == fr.APP_TITLE
    assert "suppression" in fr.DELETE_WHILE_RUNNING_MESSAGE.lower()
    assert fr.READINESS_READY_LABEL == "Pret"
    assert "heuristique" in fr.DEANON_CLASSIFICATION_NOTE
    assert "Traitement" in fr.WORKSPACE_RUNNING_MESSAGE
    assert "Attention" == fr.ERROR_BANNER_TITLE
    assert "#11161c" in window.styleSheet()
