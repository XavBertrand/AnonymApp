from __future__ import annotations

from src.app.ui_contracts.case_workspace_view_models import ReviewUpdateViewModel, SubstitutionReviewViewModel


class MappingReviewPanel:
    def __init__(self) -> None:
        self.review: SubstitutionReviewViewModel | None = None
        self.last_update: ReviewUpdateViewModel | None = None
        self._load_callback = None
        self._remove_callback = None

    def bind_actions(self, *, load_review, remove_substitutions) -> None:
        self._load_callback = load_review
        self._remove_callback = remove_substitutions

    def set_review(self, review: SubstitutionReviewViewModel | None) -> None:
        self.review = review

    def request_load_review(self, document_id: str) -> None:
        if self._load_callback is not None:
            self._load_callback(document_id)

    def request_remove_substitutions(self, mapping_entry_ids: tuple[str, ...]) -> None:
        if self._remove_callback is not None:
            self._remove_callback(mapping_entry_ids)

    def set_review_update(self, update: ReviewUpdateViewModel) -> None:
        self.last_update = update
        self.review = update.review
