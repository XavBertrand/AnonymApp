from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:  # pragma: no cover - exercised only when PySide6 is installed
    from PySide6.QtCore import QThread, QTimer
    from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget

    PYSIDE6_AVAILABLE = True

    def ensure_application() -> QApplication:
        instance = QApplication.instance()
        if instance is None:
            instance = QApplication([])
        return instance

    def dispatch_to_main_thread(callback) -> None:
        application = ensure_application()
        if application.thread() == QThread.currentThread():
            callback()
            return
        QTimer.singleShot(0, application, callback)

    def process_events() -> None:
        ensure_application().processEvents()
except ModuleNotFoundError:  # pragma: no cover - default in CI for this repository
    PYSIDE6_AVAILABLE = False

    class QWidget:
        def __init__(self, *args, **kwargs) -> None:
            _ = (args, kwargs)
            self._stylesheet = ""

        def setStyleSheet(self, stylesheet: str) -> None:
            self._stylesheet = stylesheet

        def styleSheet(self) -> str:
            return self._stylesheet

    class QMainWindow(QWidget):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self._central_widget = None
            self.window_title = ""

        def setCentralWidget(self, widget: QWidget) -> None:
            self._central_widget = widget

        def setWindowTitle(self, title: str) -> None:
            self.window_title = title

        def show(self) -> None:
            return None

    class QApplication:
        def __init__(self, _args) -> None:
            return None

        def exec(self) -> int:
            return 0

        @staticmethod
        def instance():
            return None

    class QLabel(QWidget):
        def __init__(self, text: str = "") -> None:
            super().__init__()
            self.text = text

        def setText(self, text: str) -> None:
            self.text = text

    class QPushButton(QWidget):
        def __init__(self, text: str = "") -> None:
            super().__init__()
            self.text = text
            self._callback = None

        def connect(self, callback) -> None:
            self._callback = callback

        def click(self) -> None:
            if self._callback is not None:
                self._callback()

    class QVBoxLayout:
        def __init__(self, *_args, **_kwargs) -> None:
            self.items: list[object] = []

        def addWidget(self, widget: object) -> None:
            self.items.append(widget)

    def ensure_application() -> QApplication:
        return QApplication([])

    def dispatch_to_main_thread(callback) -> None:
        callback()

    def process_events() -> None:
        return None
