from __future__ import annotations

from pathlib import Path

from src.app.desktop.presenters.workspace_presenter import WorkspacePresenter
from src.app.desktop.qt_compat import QMainWindow, dispatch_to_main_thread, ensure_application
from src.app.desktop.workers.workspace_worker import WorkspaceWorker
from src.app.desktop.widgets.case_history_panel import CaseHistoryPanel
from src.app.desktop.widgets.case_workspace_panel import CaseWorkspacePanel
from src.app.desktop.widgets.delete_case_dialog import DeleteCaseDialog
from src.app.desktop.widgets.result_preview_panel import ResultPreviewPanel
from src.services.case_workspace_service import CaseDeletionBlockedError, CaseWorkspaceService


class DesktopMainWindow(QMainWindow):
    def __init__(
        self,
        presenter: WorkspacePresenter,
        worker: WorkspaceWorker | None = None,
        delete_case_dialog: DeleteCaseDialog | None = None,
    ) -> None:
        self._application = ensure_application()
        super().__init__()
        self.presenter = presenter
        self.worker = worker or WorkspaceWorker(dispatcher=dispatch_to_main_thread)
        self.delete_case_dialog = delete_case_dialog or DeleteCaseDialog()
        self.case_history_panel = CaseHistoryPanel()
        self.case_workspace_panel = CaseWorkspacePanel()
        self.result_preview_panel = ResultPreviewPanel()
        self.current_case_id: str | None = None
        self.pending_batch = None
        self.last_error: str | None = None
        self.setWindowTitle("A4 = Action Avocats Anonym App")
        self.case_history_panel.bind_actions(
            create_case=self.create_case,
            open_case=self.open_case,
            delete_case=self.delete_case,
        )
        self.case_workspace_panel.bind_run_action(self.run_case_anonymization)

    def _apply_workspace_load(self, model) -> None:
        self.case_history_panel.set_cases(model.cases)
        if model.selected_case is None:
            self.current_case_id = None
            self.case_workspace_panel.set_workspace(None)
            self.result_preview_panel.set_artifacts(())
            return
        self.current_case_id = model.selected_case.case_id
        self.case_workspace_panel.set_workspace(model.selected_case)
        self.result_preview_panel.set_artifacts(model.selected_case.artifacts)

    def load(self) -> None:
        self._apply_workspace_load(self.presenter.load_workspace())

    def create_case(self, display_name: str) -> None:
        self.presenter.create_case(display_name)
        self._apply_workspace_load(self.presenter.load_workspace())

    def open_case(self, case_id: str) -> None:
        self.presenter.open_case(case_id)
        self._apply_workspace_load(self.presenter.load_workspace())

    def delete_case(self, case_id: str) -> None:
        item = next((case for case in self.case_history_panel.items if case.case_id == case_id), None)
        if item is None:
            raise ValueError(f"Unknown case '{case_id}'")
        if self.pending_batch is not None and self.current_case_id == case_id:
            self.last_error = CaseWorkspaceService.DELETE_WHILE_RUNNING_MESSAGE
            self.delete_case_dialog.show_blocked(self.last_error)
            return
        if not item.delete_available:
            self.last_error = item.delete_unavailable_reason
            if self.last_error is not None:
                self.delete_case_dialog.show_blocked(self.last_error)
            return
        if not self.delete_case_dialog.request_confirmation(item.display_name):
            return
        try:
            model = self.presenter.delete_case(case_id, confirmed=True)
        except CaseDeletionBlockedError as exc:
            self.last_error = str(exc)
            self.delete_case_dialog.show_blocked(self.last_error)
            return
        self._apply_workspace_load(model)

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
