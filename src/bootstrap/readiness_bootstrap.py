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


def build_backend_descriptors() -> list[BackendDescriptor]:
    dep = run_dependency_checks()
    model = run_model_checks()

    classic_checks = [
        _to_readiness_check(r.name, r.required, r.available, r.message, r.remediation)
        for r in dep
        if r.name in {"transformers", "torch", "requests", "ollama"}
    ] + [
        _to_readiness_check(r.model_name, r.required, r.available, r.message, r.remediation)
        for r in model
        if r.model_name == "camembert-ner"
    ]

    transformer_checks = [
        _to_readiness_check(r.name, r.required, r.available, r.message, r.remediation)
        for r in dep
        if r.name in {"transformers", "torch", "rapidfuzz", "unidecode", "gliner"}
    ] + [
        _to_readiness_check(r.model_name, r.required, r.available, r.message, r.remediation)
        for r in model
        if r.model_name == "gliner_multi_pii-v1"
    ]

    def status_from_checks(checks: list[ReadinessCheckResult]) -> str:
        critical_fail = any(c.severity == "critical" and c.status == "fail" for c in checks)
        warning_fail = any(c.severity == "warning" and c.status == "fail" for c in checks)
        if critical_fail:
            return "unavailable"
        if warning_fail:
            return "degraded"
        return "ready"

    return [
        BackendDescriptor(
            engine_id="classic",
            display_name="Classic HF+Regex",
            availability_status=status_from_checks(classic_checks),
            capabilities=["anonymize", "deanonymize"],
            readiness_checks=classic_checks,
        ),
        BackendDescriptor(
            engine_id="transformer",
            display_name="Transformer GLiNER",
            availability_status=status_from_checks(transformer_checks),
            capabilities=["anonymize", "deanonymize"],
            readiness_checks=transformer_checks,
        ),
    ]
