from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from src.models.mapping_artifact import MappingArtifact, MappingEntry, MappingOrigin


class CanonicalMappingAdapter:
    supported_schema_versions = {"1.0"}
    supported_mapping_format = "canonical-v1"

    def dump(self, artifact: MappingArtifact, path: Path) -> None:
        artifact.validate()
        payload = asdict(artifact)
        payload["origin"]["generated_at"] = artifact.origin.generated_at.isoformat()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self, path: Path) -> MappingArtifact:
        raw = json.loads(path.read_text(encoding="utf-8"))
        origin = raw.get("origin", {})
        artifact = MappingArtifact(
            schema_version=raw["schema_version"],
            mapping_format=raw["mapping_format"],
            origin=MappingOrigin(
                engine_id=origin["engine_id"],
                generated_at=datetime.fromisoformat(origin["generated_at"]),
                wrapper_contract_version=origin.get("wrapper_contract_version", "1.0"),
            ),
            entries=[
                MappingEntry(
                    placeholder=e["placeholder"],
                    original_value=e["original_value"],
                    entity_type=e["entity_type"],
                    position_ranges=[tuple(r) for r in e.get("position_ranges", [])],
                )
                for e in raw.get("entries", [])
            ],
            integrity_hash=raw.get("integrity_hash"),
        )
        self.validate_compatibility(artifact)
        return artifact

    def validate_compatibility(self, artifact: MappingArtifact) -> None:
        if artifact.schema_version not in self.supported_schema_versions:
            raise ValueError("unsupported_schema_version")
        if artifact.mapping_format != self.supported_mapping_format:
            raise ValueError("unsupported_mapping_format")
        if not artifact.origin.engine_id:
            raise ValueError("missing_required_metadata")
