from __future__ import annotations

from src.app.ui_contracts.case_workspace_view_models import ReadinessSummaryViewModel


class ReadinessPanel:
    def __init__(self) -> None:
        self.summary: ReadinessSummaryViewModel | None = None
        self._details_callback = None

    def bind_actions(self, *, show_details) -> None:
        self._details_callback = show_details

    def set_summary(self, summary: ReadinessSummaryViewModel) -> None:
        self.summary = summary

    def request_show_details(self) -> None:
        if self._details_callback is not None:
            self._details_callback()
