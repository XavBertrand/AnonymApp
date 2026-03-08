from __future__ import annotations

from src.bootstrap.dependency_check import run_dependency_checks
from src.bootstrap.model_check import run_model_checks
from src.models.backend_descriptor import BackendDescriptor, ReadinessCheckResult


def _to_readiness_check(name: str, required: bool, ok: bool, message: str, remediation: str | None) -> ReadinessCheckResult:
    severity = "critical" if required else "warning"
    status = "pass" if ok else "fail"
    return ReadinessCheckResult(
        check_name=name,
        severity=severity,
        status=status,
        message=message,
        remediation=remediation,
    )


def _status_from_checks(checks: list[ReadinessCheckResult]) -> str:
    critical_fail = any(c.severity == "critical" and c.status == "fail" for c in checks)
    warning_fail = any(c.severity == "warning" and c.status == "fail" for c in checks)
    if critical_fail:
        return "unavailable"
    if warning_fail:
        return "degraded"
    return "ready"


def _checks_for_backend(
    backend_id: str,
    *,
    dependency_checks: list,
    model_checks: list,
) -> list[ReadinessCheckResult]:
    checks = [
        _to_readiness_check(result.name, result.required, result.available, result.message, result.remediation)
        for result in dependency_checks
        if backend_id in result.backends
    ]
    checks.extend(
        _to_readiness_check(
            result.model_name,
            result.required,
            result.available,
            result.message,
            result.remediation,
        )
        for result in model_checks
        if backend_id in result.backends
    )
    return checks


def build_backend_descriptors() -> list[BackendDescriptor]:
    dependency_checks = run_dependency_checks()
    model_checks = run_model_checks()
    classic_checks = _checks_for_backend(
        "classic",
        dependency_checks=dependency_checks,
        model_checks=model_checks,
    )
    transformer_checks = _checks_for_backend(
        "transformer",
        dependency_checks=dependency_checks,
        model_checks=model_checks,
    )

    return [
        BackendDescriptor(
            engine_id="classic",
            display_name="Classic HF+Regex",
            availability_status=_status_from_checks(classic_checks),
            capabilities=["anonymize", "deanonymize"],
            readiness_checks=classic_checks,
        ),
        BackendDescriptor(
            engine_id="transformer",
            display_name="Transformer GLiNER",
            availability_status=_status_from_checks(transformer_checks),
            capabilities=["anonymize", "deanonymize"],
            readiness_checks=transformer_checks,
        ),
    ]
