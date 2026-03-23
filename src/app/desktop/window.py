from __future__ import annotations

from pathlib import Path

from src.app.desktop.copy import fr
from src.app.desktop.presenters.workspace_presenter import WorkspacePresenter
from src.app.desktop.qt_compat import QMainWindow, dispatch_to_main_thread, ensure_application
from src.app.desktop.workers.workspace_worker import WorkspaceWorker
from src.app.desktop.widgets.case_history_panel import CaseHistoryPanel
from src.app.desktop.widgets.mapping_review_panel import MappingReviewPanel
from src.app.desktop.widgets.case_workspace_panel import CaseWorkspacePanel
from src.app.desktop.widgets.deanonymization_panel import DeanonymizationPanel
from src.app.desktop.widgets.delete_case_dialog import DeleteCaseDialog
from src.app.desktop.widgets.error_banner import ErrorBanner
from src.app.desktop.widgets.readiness_details_dialog import ReadinessDetailsDialog
from src.app.desktop.widgets.readiness_panel import ReadinessPanel
from src.app.desktop.widgets.result_preview_panel import ResultPreviewPanel
from src.services.case_workspace_service import CaseDeletionBlockedError, CaseWorkspaceService


class DesktopMainWindow(QMainWindow):
    def __init__(
        self,
        presenter: WorkspacePresenter,
        worker: WorkspaceWorker | None = None,
        delete_case_dialog: DeleteCaseDialog | None = None,
        readiness_details_dialog: ReadinessDetailsDialog | None = None,
    ) -> None:
        self._application = ensure_application()
        super().__init__()
        self.presenter = presenter
        self.worker = worker or WorkspaceWorker(dispatcher=dispatch_to_main_thread)
        self.delete_case_dialog = delete_case_dialog or DeleteCaseDialog()
        self.readiness_details_dialog = readiness_details_dialog or ReadinessDetailsDialog()
        self.case_history_panel = CaseHistoryPanel()
        self.case_workspace_panel = CaseWorkspacePanel()
        self.mapping_review_panel = MappingReviewPanel()
        self.deanonymization_panel = DeanonymizationPanel()
        self.readiness_panel = ReadinessPanel()
        self.error_banner = ErrorBanner()
        self.result_preview_panel = ResultPreviewPanel()
        self.current_case_id: str | None = None
        self.pending_batch = None
        self.pending_deanonymization = None
        self.last_error: str | None = None
        self.setWindowTitle(fr.APP_TITLE)
        self._apply_theme()
        self.case_history_panel.bind_actions(
            create_case=self.create_case,
            open_case=self.open_case,
            delete_case=self.delete_case,
        )
        self.readiness_panel.bind_actions(show_details=self.show_readiness_details)
        self.case_workspace_panel.bind_run_action(self.run_case_anonymization)
        self.mapping_review_panel.bind_actions(
            load_review=self.load_substitution_review,
            remove_substitutions=self.remove_substitutions,
        )
        self.deanonymization_panel.bind_actions(
            deanonymize_text=self.deanonymize_pasted_text,
            export_result=self.export_deanonymized_result,
        )
        self.result_preview_panel.bind_regeneration_action(self.regenerate_stale_output)

    def _apply_workspace_load(self, model) -> None:
        self.error_banner.clear()
        self.readiness_panel.set_summary(model.readiness)
        self.case_history_panel.set_cases(model.cases)
        if model.selected_case is None:
            self.current_case_id = None
            self.case_workspace_panel.set_workspace(None)
            self.case_workspace_panel.set_status_message(None)
            self.mapping_review_panel.set_review(None)
            self.deanonymization_panel.set_session(None)
            self.result_preview_panel.set_artifacts(())
            return
        self.current_case_id = model.selected_case.case_id
        self.case_workspace_panel.set_workspace(model.selected_case)
        self.case_workspace_panel.set_status_message(None)
        self.mapping_review_panel.set_review(None)
        self.deanonymization_panel.set_session(None)
        self.result_preview_panel.set_artifacts(model.selected_case.artifacts)

    def _apply_theme(self) -> None:
        theme_path = Path(__file__).resolve().parent / "styles" / "dark_theme.qss"
        if not theme_path.exists():
            return
        stylesheet = theme_path.read_text(encoding="utf-8")
        self.setStyleSheet(stylesheet)

    def load(self) -> None:
        try:
            self._apply_workspace_load(self.presenter.load_workspace())
        except Exception as exc:
            self.last_error = str(exc)
            self.error_banner.show_error(self.last_error, title=fr.ERROR_BANNER_TITLE)

    def create_case(self, display_name: str) -> None:
        try:
            self.presenter.create_case(display_name)
            self._apply_workspace_load(self.presenter.load_workspace())
        except Exception as exc:
            self.last_error = str(exc)
            self.error_banner.show_error(self.last_error, title=fr.ERROR_BANNER_TITLE)

    def open_case(self, case_id: str) -> None:
        try:
            self.presenter.open_case(case_id)
            self._apply_workspace_load(self.presenter.load_workspace())
        except Exception as exc:
            self.last_error = str(exc)
            self.error_banner.show_error(self.last_error, title=fr.ERROR_BANNER_TITLE)

    def delete_case(self, case_id: str) -> None:
        item = next((case for case in self.case_history_panel.items if case.case_id == case_id), None)
        if item is None:
            raise ValueError(f"Unknown case '{case_id}'")
        if (self.pending_batch is not None or self.pending_deanonymization is not None) and self.current_case_id == case_id:
            self.last_error = CaseWorkspaceService.DELETE_WHILE_RUNNING_MESSAGE
            self.error_banner.show_error(self.last_error, title=fr.ERROR_BANNER_TITLE)
            self.delete_case_dialog.show_blocked(self.last_error)
            return
        if not item.delete_available:
            self.last_error = item.delete_unavailable_reason
            if self.last_error is not None:
                self.error_banner.show_error(self.last_error, title=fr.ERROR_BANNER_TITLE)
                self.delete_case_dialog.show_blocked(self.last_error)
            return
        if not self.delete_case_dialog.request_confirmation(item.display_name):
            return
        try:
            model = self.presenter.delete_case(case_id, confirmed=True)
        except CaseDeletionBlockedError as exc:
            self.last_error = str(exc)
            self.error_banner.show_error(self.last_error, title=fr.ERROR_BANNER_TITLE)
            self.delete_case_dialog.show_blocked(self.last_error)
            return
        self._apply_workspace_load(model)

    def _apply_batch_result(self, batch) -> None:
        self.pending_batch = None
        self.last_error = None
        self.error_banner.clear()
        self.case_workspace_panel.set_batch_result(batch)
        self.case_workspace_panel.set_workspace(batch.workspace)
        self.mapping_review_panel.set_review(None)
        self.result_preview_panel.set_batch_result(batch)
        self.result_preview_panel.set_artifacts(batch.workspace.artifacts)

    def _apply_batch_error(self, error: Exception) -> None:
        self.pending_batch = None
        self.last_error = str(error)
        self.error_banner.show_error(self.last_error, title=fr.ERROR_BANNER_TITLE)
        self.case_workspace_panel.set_status_message(None)

    def run_case_anonymization(self, txt_file_paths: list[Path]) -> None:
        if self.current_case_id is None:
            raise RuntimeError("A case must be selected before anonymization")
        self.last_error = None
        self.error_banner.clear()
        self.case_workspace_panel.set_status_message(fr.WORKSPACE_RUNNING_MESSAGE)
        self.pending_batch = self.worker.submit(
            self.presenter.run_case_anonymization,
            self.current_case_id,
            txt_file_paths,
            on_success=self._apply_batch_result,
            on_error=self._apply_batch_error,
        )

    def _apply_deanonymization_result(self, session) -> None:
        self.pending_deanonymization = None
        self.last_error = None
        self.error_banner.clear()
        self.case_workspace_panel.set_status_message(None)
        self.deanonymization_panel.set_session(session)

    def _apply_deanonymization_error(self, error: Exception) -> None:
        self.pending_deanonymization = None
        self.last_error = str(error)
        self.error_banner.show_error(self.last_error, title=fr.ERROR_BANNER_TITLE)
        self.case_workspace_panel.set_status_message(None)

    def load_substitution_review(self, document_id: str) -> None:
        if self.current_case_id is None:
            raise RuntimeError("A case must be selected before loading substitution review")
        try:
            review = self.presenter.load_substitution_review(self.current_case_id, document_id)
            self.mapping_review_panel.set_review(review)
        except Exception as exc:
            self.last_error = str(exc)
            self.error_banner.show_error(self.last_error, title=fr.ERROR_BANNER_TITLE)

    def remove_substitutions(self, mapping_entry_ids: tuple[str, ...]) -> None:
        if self.current_case_id is None:
            raise RuntimeError("A case must be selected before removing substitutions")
        review = self.mapping_review_panel.review
        if review is None:
            raise RuntimeError("A substitution review must be loaded before removing substitutions")
        try:
            update = self.presenter.remove_substitutions(
                self.current_case_id,
                review.document_id,
                mapping_entry_ids,
            )
            self._apply_workspace_load(self.presenter.load_workspace())
            self.mapping_review_panel.set_review_update(update)
            self.result_preview_panel.set_artifacts(update.workspace.artifacts)
        except Exception as exc:
            self.last_error = str(exc)
            self.error_banner.show_error(self.last_error, title=fr.ERROR_BANNER_TITLE)

    def regenerate_stale_output(self, artifact_id: str) -> None:
        if self.current_case_id is None:
            raise RuntimeError("A case must be selected before regenerating output")
        try:
            result = self.presenter.regenerate_stale_output(self.current_case_id, artifact_id)
            self._apply_workspace_load(self.presenter.load_workspace())
            self.result_preview_panel.set_regeneration_result(result)
            self.result_preview_panel.set_artifacts(result.workspace.artifacts)
            if result.review is not None:
                self.mapping_review_panel.set_review(result.review)
        except Exception as exc:
            self.last_error = str(exc)
            self.error_banner.show_error(self.last_error, title=fr.ERROR_BANNER_TITLE)

    def deanonymize_pasted_text(self, input_text: str) -> None:
        if self.current_case_id is None:
            raise RuntimeError("A case must be selected before deanonymization")
        self.last_error = None
        self.error_banner.clear()
        self.case_workspace_panel.set_status_message(fr.DEANON_RUNNING_MESSAGE)
        self.pending_deanonymization = self.worker.submit(
            self.presenter.deanonymize_pasted_text,
            self.current_case_id,
            input_text,
            on_success=self._apply_deanonymization_result,
            on_error=self._apply_deanonymization_error,
        )

    def export_deanonymized_result(self, destination: Path | None = None) -> None:
        if self.current_case_id is None:
            raise RuntimeError("A case must be selected before exporting deanonymized text")
        session = self.deanonymization_panel.session
        if session is None:
            raise RuntimeError("A deanonymization result must be available before export")
        try:
            result = self.presenter.export_deanonymized_result(
                self.current_case_id,
                session.session_id,
                destination,
            )
            self.case_workspace_panel.set_workspace(result.workspace)
            self.case_workspace_panel.set_status_message(None)
            self.result_preview_panel.set_artifacts(result.workspace.artifacts)
            self.deanonymization_panel.set_export_result(result)
        except Exception as exc:
            self.last_error = str(exc)
            self.error_banner.show_error(self.last_error, title=fr.ERROR_BANNER_TITLE)

    def show_readiness_details(self) -> None:
        self.readiness_details_dialog.show_details(self.presenter.get_readiness_details())
