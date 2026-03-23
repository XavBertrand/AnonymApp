from __future__ import annotations

from pathlib import Path

from src.app.ui_contracts.case_workspace_view_models import BatchRunViewModel, CaseWorkspaceViewModel


class CaseWorkspacePanel:
    def __init__(self) -> None:
        self.workspace: CaseWorkspaceViewModel | None = None
        self.last_batch: BatchRunViewModel | None = None
        self.selected_paths: tuple[Path, ...] = ()
        self.progress_messages: tuple[str, ...] = ()
        self.status_message: str | None = None
        self.file_errors: tuple[str, ...] = ()
        self._run_callback = None

    def set_workspace(self, workspace: CaseWorkspaceViewModel | None) -> None:
        self.workspace = workspace

    def set_selected_paths(self, paths: list[Path]) -> None:
        self.selected_paths = tuple(paths)

    def set_batch_result(self, batch: BatchRunViewModel) -> None:
        self.last_batch = batch
        self.progress_messages = batch.progress_messages
        self.file_errors = tuple(
            item.error_summary
            for item in batch.items
            if item.error_summary
        )
        self.status_message = None

    def bind_run_action(self, callback) -> None:
        self._run_callback = callback

    def set_status_message(self, message: str | None) -> None:
        self.status_message = message

    def request_run(self) -> None:
        if self._run_callback is not None:
            self._run_callback(list(self.selected_paths))
