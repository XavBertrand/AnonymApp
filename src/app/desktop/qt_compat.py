from __future__ import annotations

import os
import sys


def _default_qt_platform() -> str | None:
    if os.environ.get("QT_QPA_PLATFORM"):
        return None
    if os.environ.get("ANONYMAPP_FORCE_QT_OFFSCREEN") == "1":
        return "offscreen"
    if sys.platform.startswith("win"):
        return None
    if "pytest" in sys.modules:
        return "offscreen"
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        return "offscreen"
    return None


_qt_platform = _default_qt_platform()
if _qt_platform is not None:
    os.environ["QT_QPA_PLATFORM"] = _qt_platform

_prefer_stub_qt = os.environ.get("ANONYMAPP_FORCE_QT_STUBS") == "1" or "pytest" in sys.modules

try:  # pragma: no cover - exercised only when PySide6 is installed
    if _prefer_stub_qt:
        raise ModuleNotFoundError("PySide6 intentionally stubbed for test mode")
    from PySide6.QtCore import QObject, QThread, QTimer, Signal
    from PySide6.QtWidgets import (
        QApplication,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QMainWindow,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    PYSIDE6_AVAILABLE = True
    _dispatch_bridge = None

    class _DispatchBridge(QObject):
        run = Signal(object)

        def __init__(self) -> None:
            super().__init__()
            self.run.connect(self._run_callback)

        @staticmethod
        def _run_callback(callback) -> None:
            callback()

    def ensure_application() -> QApplication:
        instance = QApplication.instance()
        if instance is None:
            instance = QApplication([])
        return instance

    def dispatch_to_main_thread(callback) -> None:
        global _dispatch_bridge
        application = ensure_application()
        if application.thread() == QThread.currentThread():
            callback()
            return
        if _dispatch_bridge is None:
            _dispatch_bridge = _DispatchBridge()
            _dispatch_bridge.moveToThread(application.thread())
        _dispatch_bridge.run.emit(callback)

    def process_events() -> None:
        ensure_application().processEvents()
except ModuleNotFoundError:  # pragma: no cover - default in CI for this repository
    PYSIDE6_AVAILABLE = False

    class QWidget:
        def __init__(self, *args, **kwargs) -> None:
            _ = (args, kwargs)
            self._stylesheet = ""
            self._layout = None
            self._visible = True

        def setStyleSheet(self, stylesheet: str) -> None:
            self._stylesheet = stylesheet

        def styleSheet(self) -> str:
            return self._stylesheet

        def setLayout(self, layout) -> None:
            self._layout = layout

        def setVisible(self, visible: bool) -> None:
            self._visible = visible

        def isVisible(self) -> bool:
            return self._visible

    class QMainWindow(QWidget):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self._central_widget = None
            self.window_title = ""
            self._size = (0, 0)

        def setCentralWidget(self, widget: QWidget) -> None:
            self._central_widget = widget

        def setWindowTitle(self, title: str) -> None:
            self.window_title = title

        def windowTitle(self) -> str:
            return self.window_title

        def show(self) -> None:
            return None

        def resize(self, width: int, height: int) -> None:
            self._size = (width, height)

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
            self.word_wrap = False

        def setText(self, text: str) -> None:
            self.text = text

        def setWordWrap(self, enabled: bool) -> None:
            self.word_wrap = enabled

        def text(self) -> str:  # pragma: no cover - parity helper
            return self.text

    class _Signal:
        def __init__(self) -> None:
            self._callback = None

        def connect(self, callback) -> None:
            self._callback = callback

        def emit(self) -> None:
            if self._callback is not None:
                self._callback()

    class QPushButton(QWidget):
        def __init__(self, text: str = "") -> None:
            super().__init__()
            self.text = text
            self.clicked = _Signal()
            self.enabled = True

        def click(self) -> None:
            if self.enabled:
                self.clicked.emit()

        def setEnabled(self, enabled: bool) -> None:
            self.enabled = enabled

        def isEnabled(self) -> bool:
            return self.enabled

    class QLineEdit(QWidget):
        def __init__(self, text: str = "") -> None:
            super().__init__()
            self._text = text
            self.placeholder = ""

        def setText(self, text: str) -> None:
            self._text = text

        def text(self) -> str:
            return self._text

        def clear(self) -> None:
            self._text = ""

        def setPlaceholderText(self, text: str) -> None:
            self.placeholder = text

    class QTextEdit(QWidget):
        def __init__(self, text: str = "") -> None:
            super().__init__()
            self._text = text
            self._read_only = False
            self.placeholder = ""

        def setPlainText(self, text: str) -> None:
            self._text = text

        def toPlainText(self) -> str:
            return self._text

        def clear(self) -> None:
            self._text = ""

        def setReadOnly(self, read_only: bool) -> None:
            self._read_only = read_only

        def setPlaceholderText(self, text: str) -> None:
            self.placeholder = text

    class QListWidget(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.items: list[str] = []
            self._current_row = -1

        def clear(self) -> None:
            self.items = []
            self._current_row = -1

        def addItem(self, text: str) -> None:
            self.items.append(text)
            if self._current_row < 0:
                self._current_row = 0

        def currentRow(self) -> int:
            return self._current_row

        def setCurrentRow(self, row: int) -> None:
            self._current_row = row

        def count(self) -> int:
            return len(self.items)

    class QVBoxLayout:
        def __init__(self, *_args, **_kwargs) -> None:
            self.items: list[object] = []

        def addWidget(self, widget: object) -> None:
            self.items.append(widget)

        def addLayout(self, layout: object) -> None:
            self.items.append(layout)

    class QHBoxLayout(QVBoxLayout):
        pass

    def ensure_application() -> QApplication:
        return QApplication([])

    def dispatch_to_main_thread(callback) -> None:
        callback()

    def process_events() -> None:
        return None
