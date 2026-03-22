from __future__ import annotations

from pathlib import Path

from src.app.ui_contracts.case_workspace_view_models import BatchRunViewModel, CaseWorkspaceViewModel, WorkspaceLoadViewModel
from src.services.case_workspace_service import CaseWorkspaceService


class WorkspacePresenter:
    def __init__(self, service: CaseWorkspaceService) -> None:
        self._service = service

    def load_workspace(self) -> WorkspaceLoadViewModel:
        return self._service.load_workspace()

    def create_case(self, display_name: str) -> CaseWorkspaceViewModel:
        return self._service.create_case(display_name)

    def open_case(self, case_id: str) -> CaseWorkspaceViewModel:
        return self._service.open_case(case_id)

    def run_case_anonymization(self, case_id: str, txt_file_paths: list[Path]) -> BatchRunViewModel:
        return self._service.run_case_anonymization(case_id, txt_file_paths)
