from __future__ import annotations

from pathlib import Path

from src.app.desktop.qt_compat import QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget
from src.app.ui_contracts.case_workspace_view_models import (
    DeanonymizationExportViewModel,
    DeanonymizationSessionViewModel,
)


class DeanonymizationPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.input_text = ""
        self.session: DeanonymizationSessionViewModel | None = None
        self.last_export: DeanonymizationExportViewModel | None = None
        self._run_callback = None
        self._export_callback = None
        self.title_label = QLabel("Deanonymisation")
        self.input_editor = QTextEdit()
        self.input_editor.setPlaceholderText("Collez du texte anonymise ici")
        self.run_button = QPushButton("Deanonymiser")
        self.status_label = QLabel()
        self.result_editor = QTextEdit()
        self.result_editor.setReadOnly(True)
        self.export_path_input = QLineEdit()
        self.export_path_input.setPlaceholderText("Chemin export TXT optionnel")
        self.export_button = QPushButton("Exporter le resultat")
        layout = QVBoxLayout()
        for widget in (
            self.title_label,
            self.input_editor,
            self.run_button,
            self.status_label,
            self.result_editor,
            self.export_path_input,
            self.export_button,
        ):
            if hasattr(widget, "setWordWrap"):
                widget.setWordWrap(True)
            layout.addWidget(widget)
        self.setLayout(layout)
        self.run_button.clicked.connect(self.request_deanonymization)
        self.export_button.clicked.connect(self._on_export_clicked)
        self._refresh()

    def bind_actions(self, *, deanonymize_text, export_result) -> None:
        self._run_callback = deanonymize_text
        self._export_callback = export_result

    def set_input_text(self, input_text: str) -> None:
        self.input_text = input_text
        self.input_editor.setPlainText(input_text)

    def set_session(self, session: DeanonymizationSessionViewModel | None) -> None:
        self.session = session
        self._refresh()

    def set_export_result(self, result: DeanonymizationExportViewModel) -> None:
        self.last_export = result
        self.session = result.session
        self._refresh()

    def request_deanonymization(self) -> None:
        self.input_text = self.input_editor.toPlainText()
        if self._run_callback is not None:
            self._run_callback(self.input_text)

    def request_export(self, destination: Path | None = None) -> None:
        if self._export_callback is not None:
            self._export_callback(destination)

    def _on_export_clicked(self) -> None:
        destination = self.export_path_input.text().strip()
        self.request_export(Path(destination) if destination else None)

    def _refresh(self) -> None:
        if self.session is None:
            self.status_label.setText("Aucun resultat de deanonymisation")
            self.result_editor.setPlainText("")
            return
        self.status_label.setText(self.session.status_message)
        self.result_editor.setPlainText(self.session.result_text)
