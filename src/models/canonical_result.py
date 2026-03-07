from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class EntityReplacement:
    entity_type: str
    source_value: str
    replacement_value: str
    confidence: float | None = None
    start_offset: int | None = None
    end_offset: int | None = None


@dataclass(frozen=True)
class ProcessingMetadata:
    request_id: str
    duration_ms: int
    local_only_mode: bool = True
    warnings: list[str] = field(default_factory=list)
    optional_services_used: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class CanonicalAnonymizationResult:
    anonymized_text: str
    mapping: dict[str, Any]
    entities: list[EntityReplacement]
    engine_id: str
    processing_metadata: ProcessingMetadata
    pseudonym_metadata: dict[str, Any] | None = None

    def validate(self) -> None:
        if not self.anonymized_text:
            raise ValueError("anonymized_text must not be empty")
        if not self.engine_id:
            raise ValueError("engine_id must not be empty")
