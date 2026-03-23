from __future__ import annotations

from src.app.ui_contracts.case_workspace_view_models import (
    ArtifactItemViewModel,
    BatchRunViewModel,
    StaleArtifactRegenerationViewModel,
)


class ResultPreviewPanel:
    def __init__(self) -> None:
        self.artifacts: tuple[ArtifactItemViewModel, ...] = ()
        self.last_batch: BatchRunViewModel | None = None
        self.last_regeneration: StaleArtifactRegenerationViewModel | None = None
        self._regenerate_callback = None

    def set_artifacts(self, artifacts: tuple[ArtifactItemViewModel, ...]) -> None:
        self.artifacts = artifacts

    def set_batch_result(self, batch: BatchRunViewModel) -> None:
        self.last_batch = batch

    def bind_regeneration_action(self, callback) -> None:
        self._regenerate_callback = callback

    def set_regeneration_result(self, result: StaleArtifactRegenerationViewModel) -> None:
        self.last_regeneration = result

    def missing_artifacts(self) -> tuple[ArtifactItemViewModel, ...]:
        return tuple(item for item in self.artifacts if item.status == "missing")

    def stale_artifacts(self) -> tuple[ArtifactItemViewModel, ...]:
        return tuple(item for item in self.artifacts if item.status == "stale")

    def regenerable_artifacts(self) -> tuple[ArtifactItemViewModel, ...]:
        return tuple(item for item in self.artifacts if item.can_regenerate)

    def request_regenerate_artifact(self, artifact_id: str) -> None:
        if self._regenerate_callback is not None:
            self._regenerate_callback(artifact_id)
