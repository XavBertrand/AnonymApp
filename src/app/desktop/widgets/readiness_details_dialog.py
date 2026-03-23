from __future__ import annotations

from src.app.ui_contracts.case_workspace_view_models import ReadinessDetailsViewModel


class ReadinessDetailsDialog:
    def __init__(self) -> None:
        self.last_model: ReadinessDetailsViewModel | None = None

    def show_details(self, model: ReadinessDetailsViewModel) -> None:
        self.last_model = model
