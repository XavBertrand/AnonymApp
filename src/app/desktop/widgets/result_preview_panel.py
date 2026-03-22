from __future__ import annotations

from src.app.ui_contracts.case_workspace_view_models import ArtifactItemViewModel, BatchRunViewModel


class ResultPreviewPanel:
    def __init__(self) -> None:
        self.artifacts: tuple[ArtifactItemViewModel, ...] = ()
        self.last_batch: BatchRunViewModel | None = None

    def set_artifacts(self, artifacts: tuple[ArtifactItemViewModel, ...]) -> None:
        self.artifacts = artifacts

    def set_batch_result(self, batch: BatchRunViewModel) -> None:
        self.last_batch = batch
