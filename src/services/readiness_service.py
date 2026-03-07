from __future__ import annotations

from src.bootstrap.readiness_bootstrap import build_backend_descriptors
from src.models.backend_descriptor import BackendDescriptor


def get_readiness_report() -> list[BackendDescriptor]:
    return build_backend_descriptors()


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
