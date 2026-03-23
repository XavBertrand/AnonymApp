from __future__ import annotations

from pathlib import Path

from src.app.ui_contracts.case_workspace_view_models import (
    BatchRunViewModel,
    CaseWorkspaceViewModel,
    DeanonymizationExportViewModel,
    DeanonymizationSessionViewModel,
    ReviewUpdateViewModel,
    StaleArtifactRegenerationViewModel,
    SubstitutionReviewViewModel,
    WorkspaceLoadViewModel,
)
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

    def delete_case(self, case_id: str, *, confirmed: bool) -> WorkspaceLoadViewModel:
        return self._service.delete_case(case_id, confirmed=confirmed)

    def run_case_anonymization(self, case_id: str, txt_file_paths: list[Path]) -> BatchRunViewModel:
        return self._service.run_case_anonymization(case_id, txt_file_paths)

    def load_substitution_review(self, case_id: str, document_id: str) -> SubstitutionReviewViewModel:
        return self._service.load_substitution_review(case_id, document_id)

    def remove_substitutions(
        self,
        case_id: str,
        document_id: str,
        mapping_entry_ids: tuple[str, ...],
    ) -> ReviewUpdateViewModel:
        return self._service.remove_substitutions(case_id, document_id, mapping_entry_ids)

    def regenerate_stale_output(self, case_id: str, artifact_id: str) -> StaleArtifactRegenerationViewModel:
        return self._service.regenerate_stale_output(case_id, artifact_id)

    def deanonymize_pasted_text(self, case_id: str, input_text: str) -> DeanonymizationSessionViewModel:
        return self._service.deanonymize_pasted_text(case_id, input_text)

    def export_deanonymized_result(
        self,
        case_id: str,
        session_id: str,
        destination: Path | None = None,
    ) -> DeanonymizationExportViewModel:
        return self._service.export_deanonymized_result(case_id, session_id, destination)
