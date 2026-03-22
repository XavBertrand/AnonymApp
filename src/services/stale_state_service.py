from __future__ import annotations


class StaleStateService:
    def impacted_artifact_ids(self, *, case_id: str, removed_original_values: tuple[str, ...]) -> tuple[str, ...]:
        _ = (case_id, removed_original_values)
        return ()
