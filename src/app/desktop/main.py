from __future__ import annotations

from src.app.desktop.presenters.workspace_presenter import WorkspacePresenter
from src.app.desktop.qt_compat import QApplication, PYSIDE6_AVAILABLE
from src.app.desktop.workers.workspace_worker import WorkspaceWorker
from src.app.desktop.window import DesktopMainWindow
from src.services.case_workspace_service import CaseWorkspaceService


def build_main_window() -> DesktopMainWindow:
    service = CaseWorkspaceService()
    presenter = WorkspacePresenter(service)
    window = DesktopMainWindow(presenter, WorkspaceWorker())
    window.load()
    return window


def main() -> int:
    if not PYSIDE6_AVAILABLE:
        raise RuntimeError("PySide6 is required to launch the desktop application")
    app = QApplication([])
    window = build_main_window()
    window.show()
    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
