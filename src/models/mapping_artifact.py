from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class MappingOrigin:
    engine_id: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    wrapper_contract_version: str = "1.0"


@dataclass(frozen=True)
class MappingEntry:
    placeholder: str
    original_value: str
    entity_type: str
    position_ranges: list[tuple[int, int]] = field(default_factory=list)


@dataclass(frozen=True)
class MappingArtifact:
    schema_version: str
    mapping_format: str
    origin: MappingOrigin
    entries: list[MappingEntry]
    integrity_hash: str | None = None

    def validate(self) -> None:
        if not self.schema_version:
            raise ValueError("schema_version is required")
        if not self.origin.engine_id:
            raise ValueError("origin.engine_id is required")
        if self.mapping_format != "canonical-v1":
            raise ValueError("unsupported mapping_format")
