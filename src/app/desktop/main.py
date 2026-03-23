from __future__ import annotations

import logging

from src.app.desktop.presenters.workspace_presenter import WorkspacePresenter
from src.app.desktop.qt_compat import QApplication, PYSIDE6_AVAILABLE
from src.app.desktop.workers.workspace_worker import WorkspaceWorker
from src.app.desktop.window import DesktopMainWindow
from src.config.logging import configure_logging
from src.services.case_workspace_service import CaseWorkspaceService

LOGGER = logging.getLogger(__name__)


def build_main_window() -> DesktopMainWindow:
    service = CaseWorkspaceService()
    presenter = WorkspacePresenter(service)
    window = DesktopMainWindow(presenter, WorkspaceWorker())
    window.load()
    return window


def main() -> int:
    configure_logging()
    if not PYSIDE6_AVAILABLE:
        raise RuntimeError("PySide6 is required to launch the desktop application")
    try:
        app = QApplication([])
        window = build_main_window()
        window.show()
        return app.exec()
    except Exception:
        LOGGER.exception("Desktop startup failed")
        raise


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
