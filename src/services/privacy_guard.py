from __future__ import annotations

import json

from src.models.backend_descriptor import BackendDescriptor


class PrivacyGuard:
    @staticmethod
    def preview_text(text: str, *, limit: int = 80) -> str:
        compact = " ".join(text.split())
        return compact[:limit]

    @staticmethod
    def readiness_snapshot(report: list[BackendDescriptor]) -> str:
        payload = [
            {
                "engine_id": item.engine_id,
                "availability_status": item.availability_status,
            }
            for item in report
        ]
        return json.dumps(payload, ensure_ascii=False)
