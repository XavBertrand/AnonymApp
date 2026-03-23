from __future__ import annotations

from src.app.desktop.qt_compat import QLabel, QPushButton, QVBoxLayout, QWidget
from src.app.ui_contracts.case_workspace_view_models import ReadinessSummaryViewModel


class ReadinessPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.summary: ReadinessSummaryViewModel | None = None
        self._details_callback = None
        self.title_label = QLabel("Preparation")
        self.summary_label = QLabel("Etat indisponible")
        self.details_button = QPushButton("Voir les details")
        layout = QVBoxLayout()
        for widget in (self.title_label, self.summary_label, self.details_button):
            if hasattr(widget, "setWordWrap"):
                widget.setWordWrap(True)
            layout.addWidget(widget)
        self.setLayout(layout)
        self.details_button.clicked.connect(self.request_show_details)

    def bind_actions(self, *, show_details) -> None:
        self._details_callback = show_details

    def set_summary(self, summary: ReadinessSummaryViewModel) -> None:
        self.summary = summary
        message = summary.message or ""
        self.summary_label.setText(f"{summary.label} | {message}".rstrip(" |"))

    def request_show_details(self) -> None:
        if self._details_callback is not None:
            self._details_callback()
