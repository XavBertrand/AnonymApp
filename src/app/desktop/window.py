from __future__ import annotations

from pathlib import Path

from src.app.desktop.presenters.workspace_presenter import WorkspacePresenter
from src.app.desktop.qt_compat import QMainWindow, dispatch_to_main_thread, ensure_application
from src.app.desktop.workers.workspace_worker import WorkspaceWorker
from src.app.desktop.widgets.case_history_panel import CaseHistoryPanel
from src.app.desktop.widgets.case_workspace_panel import CaseWorkspacePanel
from src.app.desktop.widgets.result_preview_panel import ResultPreviewPanel


class DesktopMainWindow(QMainWindow):
    def __init__(self, presenter: WorkspacePresenter, worker: WorkspaceWorker | None = None) -> None:
        self._application = ensure_application()
        super().__init__()
        self.presenter = presenter
        self.worker = worker or WorkspaceWorker(dispatcher=dispatch_to_main_thread)
        self.case_history_panel = CaseHistoryPanel()
        self.case_workspace_panel = CaseWorkspacePanel()
        self.result_preview_panel = ResultPreviewPanel()
        self.current_case_id: str | None = None
        self.pending_batch = None
        self.last_error: str | None = None
        self.setWindowTitle("A4 = Action Avocats Anonym App")
        self.case_history_panel.bind_actions(create_case=self.create_case, open_case=self.open_case)
        self.case_workspace_panel.bind_run_action(self.run_case_anonymization)

    def load(self) -> None:
        model = self.presenter.load_workspace()
        self.case_history_panel.set_cases(model.cases)
        if model.selected_case is not None:
            self.current_case_id = model.selected_case.case_id
            self.case_workspace_panel.set_workspace(model.selected_case)
            self.result_preview_panel.set_artifacts(model.selected_case.artifacts)

    def create_case(self, display_name: str) -> None:
        workspace = self.presenter.create_case(display_name)
        self.current_case_id = workspace.case_id
        self.case_workspace_panel.set_workspace(workspace)

    def open_case(self, case_id: str) -> None:
        workspace = self.presenter.open_case(case_id)
        self.current_case_id = workspace.case_id
        self.case_workspace_panel.set_workspace(workspace)
        self.result_preview_panel.set_artifacts(workspace.artifacts)

    def _apply_batch_result(self, batch) -> None:
        self.pending_batch = None
        self.last_error = None
        self.case_workspace_panel.set_batch_result(batch)
        self.case_workspace_panel.set_workspace(batch.workspace)
        self.result_preview_panel.set_batch_result(batch)
        self.result_preview_panel.set_artifacts(batch.workspace.artifacts)

    def _apply_batch_error(self, error: Exception) -> None:
        self.pending_batch = None
        self.last_error = str(error)

    def run_case_anonymization(self, txt_file_paths: list[Path]) -> None:
        if self.current_case_id is None:
            raise RuntimeError("A case must be selected before anonymization")
        self.pending_batch = self.worker.submit(
            self.presenter.run_case_anonymization,
            self.current_case_id,
            txt_file_paths,
            on_success=self._apply_batch_result,
            on_error=self._apply_batch_error,
        )
