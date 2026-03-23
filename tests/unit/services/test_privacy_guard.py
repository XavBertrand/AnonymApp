from __future__ import annotations

import json

from src.models.backend_descriptor import BackendDescriptor
from src.services.privacy_guard import PrivacyGuard


def test_privacy_guard_compacts_and_limits_preview_text() -> None:
    preview = PrivacyGuard.preview_text("Alice   arrive\navec   Bob", limit=12)

    assert preview == "Alice arrive"


def test_privacy_guard_reduces_readiness_snapshot_to_minimal_fields() -> None:
    snapshot = PrivacyGuard.readiness_snapshot(
        [
            BackendDescriptor(
                engine_id="transformer",
                display_name="Transformer",
                availability_status="ready",
                readiness_checks=[],
            )
        ]
    )

    assert json.loads(snapshot) == [{"engine_id": "transformer", "availability_status": "ready"}]


def test_privacy_guard_does_not_leak_check_messages_or_remediation_into_snapshot() -> None:
    snapshot = PrivacyGuard.readiness_snapshot(
        [
            BackendDescriptor(
                engine_id="transformer",
                display_name="Transformer",
                availability_status="unavailable",
                readiness_checks=[],
            )
        ]
    )

    assert "Transformer" not in snapshot
    assert "remediation" not in snapshot


def test_privacy_guard_truncates_long_preview_text() -> None:
    preview = PrivacyGuard.preview_text("Alice " * 30, limit=20)

    assert len(preview) == 20
