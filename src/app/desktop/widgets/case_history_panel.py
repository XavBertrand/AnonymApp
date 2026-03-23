from __future__ import annotations

from src.app.desktop.qt_compat import QLabel, QLineEdit, QListWidget, QPushButton, QVBoxLayout, QWidget
from src.app.ui_contracts.case_workspace_view_models import CaseListItemViewModel


class CaseHistoryPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.items: tuple[CaseListItemViewModel, ...] = ()
        self._create_case_callback = None
        self._open_case_callback = None
        self._delete_case_callback = None
        self.last_delete_block_reason: str | None = None
        self._case_ids_by_row: list[str] = []
        self.title_label = QLabel("Dossiers")
        self.create_case_input = QLineEdit()
        self.create_case_input.setPlaceholderText("Nom du dossier")
        self.create_case_button = QPushButton("Creer le dossier")
        self.case_list = QListWidget()
        self.open_case_button = QPushButton("Ouvrir")
        self.delete_case_button = QPushButton("Supprimer")
        self.summary_label = QLabel("Aucun dossier")
        layout = QVBoxLayout()
        for widget in (
            self.title_label,
            self.create_case_input,
            self.create_case_button,
            self.case_list,
            self.open_case_button,
            self.delete_case_button,
            self.summary_label,
        ):
            if hasattr(widget, "setWordWrap"):
                widget.setWordWrap(True)
            layout.addWidget(widget)
        self.setLayout(layout)
        self.create_case_button.clicked.connect(self._on_create_clicked)
        self.open_case_button.clicked.connect(self._on_open_clicked)
        self.delete_case_button.clicked.connect(self._on_delete_clicked)
        self._refresh_summary()

    def set_cases(self, items: tuple[CaseListItemViewModel, ...]) -> None:
        self.items = items
        self._case_ids_by_row = [item.case_id for item in items]
        self.case_list.clear()
        for item in items:
            suffix = ""
            if not item.delete_available and item.delete_unavailable_reason:
                suffix = f" | suppression indisponible: {item.delete_unavailable_reason}"
            self.case_list.addItem(f"{item.display_name} | {item.status_summary}{suffix}")
        self._refresh_summary()

    def bind_actions(self, *, create_case, open_case, delete_case=None) -> None:
        self._create_case_callback = create_case
        self._open_case_callback = open_case
        self._delete_case_callback = delete_case

    def request_create_case(self, display_name: str) -> None:
        if self._create_case_callback is not None:
            self._create_case_callback(display_name)
        self.create_case_input.clear()

    def request_open_case(self, case_id: str | None = None) -> None:
        resolved_case_id = case_id or self._selected_case_id()
        if resolved_case_id is None:
            return
        if self._open_case_callback is not None:
            self._open_case_callback(resolved_case_id)

    def request_delete_case(self, case_id: str | None = None) -> None:
        resolved_case_id = case_id or self._selected_case_id()
        if resolved_case_id is None:
            return
        item = next((case for case in self.items if case.case_id == resolved_case_id), None)
        if item is not None and not item.delete_available:
            self.last_delete_block_reason = item.delete_unavailable_reason
            self._refresh_summary()
            return
        if self._delete_case_callback is not None:
            self._delete_case_callback(resolved_case_id)

    def _selected_case_id(self) -> str | None:
        row = self.case_list.currentRow()
        if row < 0 or row >= len(self._case_ids_by_row):
            return None
        return self._case_ids_by_row[row]

    def _refresh_summary(self) -> None:
        self.summary_label.setText(f"Dossiers connus: {len(self.items)}")

    def _on_create_clicked(self) -> None:
        display_name = self.create_case_input.text().strip()
        if display_name:
            self.request_create_case(display_name)

    def _on_open_clicked(self) -> None:
        self.request_open_case()

    def _on_delete_clicked(self) -> None:
        self.request_delete_case()
