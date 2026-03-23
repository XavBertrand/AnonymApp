from __future__ import annotations

from pathlib import Path

from src.app.desktop.qt_compat import QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget
from src.app.ui_contracts.case_workspace_view_models import BatchRunViewModel, CaseWorkspaceViewModel


class CaseWorkspacePanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.workspace: CaseWorkspaceViewModel | None = None
        self.last_batch: BatchRunViewModel | None = None
        self.selected_paths: tuple[Path, ...] = ()
        self.progress_messages: tuple[str, ...] = ()
        self.status_message: str | None = None
        self.file_errors: tuple[str, ...] = ()
        self._run_callback = None
        self.title_label = QLabel("Workspace")
        self.workspace_label = QLabel("Aucun dossier selectionne")
        self.paths_input = QTextEdit()
        self.paths_input.setPlaceholderText("Chemins TXT, un par ligne")
        self.run_button = QPushButton("Lancer l'anonymisation TXT")
        self.status_label = QLabel()
        self.progress_label = QLabel()
        self.errors_label = QLabel()
        layout = QVBoxLayout()
        for widget in (
            self.title_label,
            self.workspace_label,
            self.paths_input,
            self.run_button,
            self.status_label,
            self.progress_label,
            self.errors_label,
        ):
            if hasattr(widget, "setWordWrap"):
                widget.setWordWrap(True)
            layout.addWidget(widget)
        self.setLayout(layout)
        self.run_button.clicked.connect(self.request_run)
        self._refresh()

    def set_workspace(self, workspace: CaseWorkspaceViewModel | None) -> None:
        self.workspace = workspace
        self._refresh()

    def set_selected_paths(self, paths: list[Path]) -> None:
        self.selected_paths = tuple(paths)
        self.paths_input.setPlainText("\n".join(str(path) for path in self.selected_paths))

    def set_batch_result(self, batch: BatchRunViewModel) -> None:
        self.last_batch = batch
        self.progress_messages = batch.progress_messages
        self.file_errors = tuple(
            item.error_summary
            for item in batch.items
            if item.error_summary
        )
        self.status_message = None
        self._refresh()

    def bind_run_action(self, callback) -> None:
        self._run_callback = callback

    def set_status_message(self, message: str | None) -> None:
        self.status_message = message
        self._refresh()

    def request_run(self) -> None:
        raw_paths = [line.strip() for line in self.paths_input.toPlainText().splitlines() if line.strip()]
        if raw_paths:
            self.selected_paths = tuple(Path(item) for item in raw_paths)
        if self._run_callback is not None:
            self._run_callback(list(self.selected_paths))

    def _refresh(self) -> None:
        if self.workspace is None:
            self.workspace_label.setText("Aucun dossier selectionne")
        else:
            self.workspace_label.setText(
                f"Dossier: {self.workspace.display_name} | statut={self.workspace.status_summary} | "
                f"mapping={self.workspace.active_mapping_revision}"
            )
        self.status_label.setText(self.status_message or "Statut: inactif")
        self.progress_label.setText(
            "Progression:\n" + "\n".join(self.progress_messages)
            if self.progress_messages
            else "Progression: aucune"
        )
        self.errors_label.setText(
            "Erreurs fichiers:\n" + "\n".join(self.file_errors)
            if self.file_errors
            else "Erreurs fichiers: aucune"
        )
