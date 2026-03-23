from __future__ import annotations

from pathlib import Path

from src.app.ui_contracts.case_workspace_view_models import (
    DeanonymizationExportViewModel,
    DeanonymizationSessionViewModel,
)


class DeanonymizationPanel:
    def __init__(self) -> None:
        self.input_text = ""
        self.session: DeanonymizationSessionViewModel | None = None
        self.last_export: DeanonymizationExportViewModel | None = None
        self._run_callback = None
        self._export_callback = None

    def bind_actions(self, *, deanonymize_text, export_result) -> None:
        self._run_callback = deanonymize_text
        self._export_callback = export_result

    def set_input_text(self, input_text: str) -> None:
        self.input_text = input_text

    def set_session(self, session: DeanonymizationSessionViewModel | None) -> None:
        self.session = session

    def set_export_result(self, result: DeanonymizationExportViewModel) -> None:
        self.last_export = result
        self.session = result.session

    def request_deanonymization(self) -> None:
        if self._run_callback is not None:
            self._run_callback(self.input_text)

    def request_export(self, destination: Path | None = None) -> None:
        if self._export_callback is not None:
            self._export_callback(destination)
