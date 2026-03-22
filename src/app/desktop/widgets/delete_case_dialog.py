from __future__ import annotations


class DeleteCaseDialog:
    def __init__(self) -> None:
        self.last_requested_display_name: str | None = None
        self.last_blocked_message: str | None = None
        self._next_response = False

    def set_next_response(self, confirmed: bool) -> None:
        self._next_response = confirmed

    def request_confirmation(self, display_name: str) -> bool:
        self.last_requested_display_name = display_name
        return self._next_response

    def show_blocked(self, message: str) -> None:
        self.last_blocked_message = message
