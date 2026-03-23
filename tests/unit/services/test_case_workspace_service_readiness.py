from __future__ import annotations

import pytest

from src.models.backend_descriptor import BackendDescriptor, ReadinessCheckResult
from src.services.readiness_service import ReadinessService
from tests.helpers.desktop_workspace_fakes import build_workspace_service


def _readiness_service(*, status: str) -> ReadinessService:
    def _provider() -> list[BackendDescriptor]:
        return [
            BackendDescriptor(
                engine_id="transformer",
                display_name="Transformer",
                availability_status=status,
                readiness_checks=[
                    ReadinessCheckResult(
                        check_name="models",
                        severity="critical",
                        status="pass" if status == "ready" else "fail",
                        message="ready" if status == "ready" else "missing",
                        remediation=None if status == "ready" else "Install models",
                    )
                ],
            )
        ]

    return ReadinessService(bootstrap_provider=_provider)


def test_case_workspace_service_maps_ready_readiness_details(tmp_path) -> None:
    service = build_workspace_service(tmp_path, readiness_service=_readiness_service(status="ready"))

    load = service.load_workspace()
    details = service.get_readiness_details()

    assert load.readiness.state == "ready"
    assert load.readiness.message is not None
    assert details.state == "ready"
    assert details.backends[0].checks[0].status == "pass"


def test_case_workspace_service_maps_blocked_readiness_details(tmp_path) -> None:
    service = build_workspace_service(tmp_path, readiness_service=_readiness_service(status="unavailable"))

    load = service.load_workspace()
    details = service.get_readiness_details()

    assert load.readiness.state == "blocked"
    assert "transformer" in load.readiness.details
    assert details.backends[0].checks[0].remediation == "Install models"


def test_case_workspace_service_blocks_anonymization_and_deanonymization_when_readiness_is_blocked(tmp_path) -> None:
    service = build_workspace_service(tmp_path, readiness_service=_readiness_service(status="unavailable"))

    workspace = service.create_case("Dossier Blocked")

    with pytest.raises(ValueError, match="indisponible|Install models"):
        service.run_case_anonymization(workspace.case_id, [])

    with pytest.raises(ValueError, match="indisponible|Install models"):
        service.deanonymize_pasted_text(workspace.case_id, "<PERSON_1>")
