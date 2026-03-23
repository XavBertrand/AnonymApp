from __future__ import annotations


class ErrorBanner:
    def __init__(self) -> None:
        self.message: str | None = None
        self.title: str | None = None

    def show_error(self, message: str, *, title: str | None = None) -> None:
        self.message = message
        self.title = title

    def clear(self) -> None:
        self.message = None
        self.title = None
