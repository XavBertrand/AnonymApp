from __future__ import annotations

from src.app.desktop.copy import fr
from src.app.ui_contracts.case_workspace_view_models import (
    ReadinessBackendViewModel,
    ReadinessCheckItemViewModel,
    ReadinessDetailsViewModel,
    ReadinessSummaryViewModel,
)
from src.services.readiness_service import ReadinessService


class ReadinessPresentationService:
    def __init__(self, readiness_service: ReadinessService) -> None:
        self._readiness_service = readiness_service

    def summary(self) -> ReadinessSummaryViewModel:
        report = self._readiness_service.get_readiness_report()
        unavailable = [item.engine_id for item in report if item.availability_status == "unavailable"]
        if unavailable:
            return ReadinessSummaryViewModel(
                state="blocked",
                label=fr.READINESS_BLOCKED_LABEL,
                message=fr.READINESS_BLOCKED_MESSAGE,
                details=tuple(unavailable),
            )
        return ReadinessSummaryViewModel(
            state="ready",
            label=fr.READINESS_READY_LABEL,
            message=fr.READINESS_READY_MESSAGE,
            details=tuple(item.engine_id for item in report),
        )

    def details(self) -> ReadinessDetailsViewModel:
        report = self._readiness_service.get_readiness_report()
        summary = self.summary()
        return ReadinessDetailsViewModel(
            state=summary.state,
            label=summary.label,
            message=summary.message,
            backends=tuple(
                ReadinessBackendViewModel(
                    engine_id=item.engine_id,
                    display_name=item.display_name,
                    availability_status=item.availability_status,
                    checks=tuple(
                        ReadinessCheckItemViewModel(
                            check_name=check.check_name,
                            status=check.status,
                            severity=check.severity,
                            message=check.message,
                            remediation=check.remediation,
                        )
                        for check in item.readiness_checks
                    ),
                )
                for item in report
            ),
        )

    def assert_operation_allowed(self, operation: str) -> None:
        details = self.details()
        if details.state != "blocked":
            return
        remediation = []
        for backend in details.backends:
            for check in backend.checks:
                if check.remediation:
                    remediation.append(check.remediation)
        message = details.message or fr.READINESS_BLOCKED_MESSAGE
        if remediation:
            unique = " | ".join(dict.fromkeys(remediation))
            raise ValueError(f"{message} {unique}")
        raise ValueError(message)
