from __future__ import annotations

from src.app.desktop.qt_compat import QLabel, QLineEdit, QListWidget, QPushButton, QTextEdit, QVBoxLayout, QWidget
from src.app.ui_contracts.case_workspace_view_models import (
    DocumentItemViewModel,
    ReviewUpdateViewModel,
    SubstitutionReviewViewModel,
)


class MappingReviewPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.review: SubstitutionReviewViewModel | None = None
        self.last_update: ReviewUpdateViewModel | None = None
        self._load_callback = None
        self._remove_callback = None
        self._documents: tuple[DocumentItemViewModel, ...] = ()
        self._document_ids_by_row: list[str] = []
        self._entry_ids_by_row: list[str] = []
        self.title_label = QLabel("Revue des substitutions")
        self.document_list = QListWidget()
        self.document_id_input = QLineEdit()
        self.document_id_input.setPlaceholderText("Document ID")
        self.load_button = QPushButton("Charger la revue")
        self.review_status_label = QLabel()
        self.substitution_list = QListWidget()
        self.remove_button = QPushButton("Supprimer la substitution selectionnee")
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        layout = QVBoxLayout()
        for widget in (
            self.title_label,
            self.document_list,
            self.document_id_input,
            self.load_button,
            self.review_status_label,
            self.substitution_list,
            self.remove_button,
            self.preview_text,
        ):
            if hasattr(widget, "setWordWrap"):
                widget.setWordWrap(True)
            layout.addWidget(widget)
        self.setLayout(layout)
        self.document_list.setCurrentRow(0)
        self.load_button.clicked.connect(self._on_load_clicked)
        self.remove_button.clicked.connect(self._on_remove_clicked)
        self._refresh()

    def bind_actions(self, *, load_review, remove_substitutions) -> None:
        self._load_callback = load_review
        self._remove_callback = remove_substitutions

    def set_review(self, review: SubstitutionReviewViewModel | None) -> None:
        self.review = review
        if review is not None:
            self.document_id_input.setText(review.document_id)
        self._refresh()

    def set_documents(self, documents: tuple[DocumentItemViewModel, ...]) -> None:
        self._documents = documents
        self._document_ids_by_row = [item.document_id for item in documents]
        self.document_list.clear()
        for item in documents:
            self.document_list.addItem(f"{item.source_filename} | {item.status}")
        if documents and not self.document_id_input.text().strip():
            self.document_id_input.setText(documents[0].document_id)

    def request_load_review(self, document_id: str) -> None:
        if self._load_callback is not None:
            self._load_callback(document_id)

    def request_remove_substitutions(self, mapping_entry_ids: tuple[str, ...]) -> None:
        if self._remove_callback is not None:
            self._remove_callback(mapping_entry_ids)

    def set_review_update(self, update: ReviewUpdateViewModel) -> None:
        self.last_update = update
        self.review = update.review
        self._refresh()

    def _refresh(self) -> None:
        self.substitution_list.clear()
        self._entry_ids_by_row = []
        if self.review is None:
            self.review_status_label.setText("Aucune revue chargee")
            self.preview_text.setPlainText("")
            return
        self.review_status_label.setText(
            f"Document: {self.review.document_name} | statut={self.review.artifact_status} | "
            f"editable={self.review.editable}"
        )
        for row in self.review.substitutions:
            suffix = ""
            if not row.removable and row.unavailable_reason:
                suffix = f" | indisponible: {row.unavailable_reason}"
            self.substitution_list.addItem(
                f"{row.original_value} -> {row.replacement_value} ({row.entity_type}){suffix}"
            )
            self._entry_ids_by_row.append(row.mapping_entry_id)
        self.preview_text.setPlainText(self.review.preview_text)

    def _on_load_clicked(self) -> None:
        row = self.document_list.currentRow()
        if 0 <= row < len(self._document_ids_by_row):
            self.document_id_input.setText(self._document_ids_by_row[row])
        document_id = self.document_id_input.text().strip()
        if document_id:
            self.request_load_review(document_id)

    def _on_remove_clicked(self) -> None:
        row = self.substitution_list.currentRow()
        if row < 0 or row >= len(self._entry_ids_by_row):
            return
        self.request_remove_substitutions((self._entry_ids_by_row[row],))
