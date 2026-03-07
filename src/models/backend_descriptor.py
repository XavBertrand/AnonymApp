from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

AvailabilityStatus = Literal["ready", "degraded", "unavailable"]
CheckSeverity = Literal["critical", "warning"]
CheckStatus = Literal["pass", "fail"]


@dataclass(frozen=True)
class ReadinessCheckResult:
    check_name: str
    severity: CheckSeverity
    status: CheckStatus
    message: str
    remediation: str | None = None


@dataclass(frozen=True)
class BackendDescriptor:
    engine_id: str
    display_name: str
    availability_status: AvailabilityStatus
    capabilities: list[str] = field(default_factory=list)
    readiness_checks: list[ReadinessCheckResult] = field(default_factory=list)
    last_checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
