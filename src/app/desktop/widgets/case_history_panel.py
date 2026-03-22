from __future__ import annotations

from src.app.ui_contracts.case_workspace_view_models import CaseListItemViewModel


class CaseHistoryPanel:
    def __init__(self) -> None:
        self.items: tuple[CaseListItemViewModel, ...] = ()
        self._create_case_callback = None
        self._open_case_callback = None

    def set_cases(self, items: tuple[CaseListItemViewModel, ...]) -> None:
        self.items = items

    def bind_actions(self, *, create_case, open_case) -> None:
        self._create_case_callback = create_case
        self._open_case_callback = open_case

    def request_create_case(self, display_name: str) -> None:
        if self._create_case_callback is not None:
            self._create_case_callback(display_name)

    def request_open_case(self, case_id: str) -> None:
        if self._open_case_callback is not None:
            self._open_case_callback(case_id)
