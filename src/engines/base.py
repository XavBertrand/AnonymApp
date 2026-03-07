from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from src.models.backend_descriptor import BackendDescriptor, ReadinessCheckResult
from src.models.canonical_result import CanonicalAnonymizationResult
from src.models.mapping_artifact import MappingArtifact


@dataclass(frozen=True)
class EngineInitConfig:
    engine_id: str
    options: dict[str, Any]


class EngineWrapper(Protocol):
    engine_id: str

    def initialize(self, config: EngineInitConfig) -> BackendDescriptor:
        ...

    def anonymize(self, text: str, options: dict[str, Any] | None = None) -> CanonicalAnonymizationResult:
        ...

    def deanonymize(self, anonymized_text: str, mapping_artifact: MappingArtifact) -> str:
        ...

    def readiness_checks(self) -> list[ReadinessCheckResult]:
        ...
