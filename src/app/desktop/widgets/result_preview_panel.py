from __future__ import annotations

from src.app.desktop.qt_compat import QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget
from src.app.ui_contracts.case_workspace_view_models import (
    ArtifactItemViewModel,
    BatchRunViewModel,
    StaleArtifactRegenerationViewModel,
)


class ResultPreviewPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.artifacts: tuple[ArtifactItemViewModel, ...] = ()
        self.last_batch: BatchRunViewModel | None = None
        self.last_regeneration: StaleArtifactRegenerationViewModel | None = None
        self._regenerate_callback = None
        self._artifact_ids_by_row: list[str] = []
        self.title_label = QLabel("Resultats / artefacts")
        self.artifact_list = QListWidget()
        self.regenerate_button = QPushButton("Regenerer l'artefact selectionne")
        self.summary_label = QLabel("Aucun artefact")
        layout = QVBoxLayout()
        for widget in (self.title_label, self.artifact_list, self.regenerate_button, self.summary_label):
            if hasattr(widget, "setWordWrap"):
                widget.setWordWrap(True)
            layout.addWidget(widget)
        self.setLayout(layout)
        self.regenerate_button.clicked.connect(self._on_regenerate_clicked)

    def set_artifacts(self, artifacts: tuple[ArtifactItemViewModel, ...]) -> None:
        self.artifacts = artifacts
        self._artifact_ids_by_row = [item.artifact_id for item in artifacts]
        self.artifact_list.clear()
        for item in artifacts:
            suffix = ""
            if item.can_regenerate:
                suffix = " | regenerable"
            elif item.regeneration_unavailable_reason:
                suffix = f" | {item.regeneration_unavailable_reason}"
            self.artifact_list.addItem(f"{item.display_name} | {item.status}{suffix}")
        self._refresh_summary()

    def set_batch_result(self, batch: BatchRunViewModel) -> None:
        self.last_batch = batch
        self._refresh_summary()

    def bind_regeneration_action(self, callback) -> None:
        self._regenerate_callback = callback

    def set_regeneration_result(self, result: StaleArtifactRegenerationViewModel) -> None:
        self.last_regeneration = result
        self._refresh_summary()

    def missing_artifacts(self) -> tuple[ArtifactItemViewModel, ...]:
        return tuple(item for item in self.artifacts if item.status == "missing")

    def stale_artifacts(self) -> tuple[ArtifactItemViewModel, ...]:
        return tuple(item for item in self.artifacts if item.status == "stale")

    def regenerable_artifacts(self) -> tuple[ArtifactItemViewModel, ...]:
        return tuple(item for item in self.artifacts if item.can_regenerate)

    def request_regenerate_artifact(self, artifact_id: str) -> None:
        if self._regenerate_callback is not None:
            self._regenerate_callback(artifact_id)

    def _on_regenerate_clicked(self) -> None:
        row = self.artifact_list.currentRow()
        if row < 0 or row >= len(self._artifact_ids_by_row):
            return
        self.request_regenerate_artifact(self._artifact_ids_by_row[row])

    def _refresh_summary(self) -> None:
        current_count = sum(item.status == "current" for item in self.artifacts)
        stale_count = sum(item.status == "stale" for item in self.artifacts)
        self.summary_label.setText(
            f"Artefacts: total={len(self.artifacts)} | current={current_count} | stale={stale_count}"
        )
