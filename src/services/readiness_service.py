from __future__ import annotations

from collections.abc import Callable

from src.bootstrap.readiness_bootstrap import build_backend_descriptors
from src.models.backend_descriptor import BackendDescriptor


class ReadinessError(RuntimeError):
    def __init__(self, *, engine_id: str, operation: str, detail: str, remediation: str | None = None) -> None:
        message = f"Backend '{engine_id}' is unavailable for {operation}. {detail}"
        if remediation:
            message = f"{message} Remediation: {remediation}"
        super().__init__(message)
        self.engine_id = engine_id
        self.operation = operation
        self.detail = detail
        self.remediation = remediation


class ReadinessService:
    def __init__(
        self,
        *,
        bootstrap_provider: Callable[[], list[BackendDescriptor]] | None = None,
    ) -> None:
        self._bootstrap_provider = bootstrap_provider or build_backend_descriptors
        self._cached_report: list[BackendDescriptor] | None = None

    def get_readiness_report(self, *, refresh: bool = False) -> list[BackendDescriptor]:
        if refresh or self._cached_report is None:
            self._cached_report = self._bootstrap_provider()
        return list(self._cached_report)

    def get_backend_descriptor(self, engine_id: str, *, refresh: bool = False) -> BackendDescriptor | None:
        report = self.get_readiness_report(refresh=refresh)
        for descriptor in report:
            if descriptor.engine_id == engine_id:
                return descriptor
        return None

    def assert_backend_usable(self, engine_id: str, *, operation: str, refresh: bool = False) -> BackendDescriptor:
        descriptor = self.get_backend_descriptor(engine_id, refresh=refresh)
        if descriptor is None:
            raise ReadinessError(
                engine_id=engine_id,
                operation=operation,
                detail="Backend is not configured in this runtime.",
                remediation="Select a supported backend and rerun readiness.",
            )

        if descriptor.availability_status != "unavailable":
            return descriptor

        failed_critical = [
            check for check in descriptor.readiness_checks if check.severity == "critical" and check.status == "fail"
        ]
        detail = "; ".join(f"{check.check_name}: {check.message}" for check in failed_critical) or (
            "Critical readiness checks failed."
        )
        remediations = sorted(
            {
                check.remediation.strip()
                for check in failed_critical
                if check.remediation and check.remediation.strip()
            }
        )
        remediation = " | ".join(remediations) if remediations else None
        raise ReadinessError(
            engine_id=engine_id,
            operation=operation,
            detail=detail,
            remediation=remediation,
        )


_DEFAULT_READINESS_SERVICE = ReadinessService()


def get_readiness_report(*, refresh: bool = False) -> list[BackendDescriptor]:
    return _DEFAULT_READINESS_SERVICE.get_readiness_report(refresh=refresh)


def format_readiness_report(descriptors: list[BackendDescriptor]) -> str:
    lines: list[str] = []
    for desc in descriptors:
        lines.append(f"[{desc.engine_id}] {desc.availability_status}")
        for check in desc.readiness_checks:
            line = f"  - {check.check_name}: {check.status} ({check.severity}) - {check.message}"
            lines.append(line)
            if check.remediation:
                lines.append(f"    remediation: {check.remediation}")
    return "\n".join(lines)

