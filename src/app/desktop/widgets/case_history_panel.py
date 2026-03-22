from __future__ import annotations

from src.app.ui_contracts.case_workspace_view_models import CaseListItemViewModel


class CaseHistoryPanel:
    def __init__(self) -> None:
        self.items: tuple[CaseListItemViewModel, ...] = ()
        self._create_case_callback = None
        self._open_case_callback = None
        self._delete_case_callback = None
        self.last_delete_block_reason: str | None = None

    def set_cases(self, items: tuple[CaseListItemViewModel, ...]) -> None:
        self.items = items

    def bind_actions(self, *, create_case, open_case, delete_case=None) -> None:
        self._create_case_callback = create_case
        self._open_case_callback = open_case
        self._delete_case_callback = delete_case

    def request_create_case(self, display_name: str) -> None:
        if self._create_case_callback is not None:
            self._create_case_callback(display_name)

    def request_open_case(self, case_id: str) -> None:
        if self._open_case_callback is not None:
            self._open_case_callback(case_id)

    def request_delete_case(self, case_id: str) -> None:
        item = next((case for case in self.items if case.case_id == case_id), None)
        if item is not None and not item.delete_available:
            self.last_delete_block_reason = item.delete_unavailable_reason
            return
        if self._delete_case_callback is not None:
            self._delete_case_callback(case_id)
