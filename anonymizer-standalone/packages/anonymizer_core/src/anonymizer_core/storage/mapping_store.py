"""Clear-text reversible mapping persistence for standalone offline usage."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from anonymizer_core.errors import InputValidationError
from anonymizer_core.storage.fs_security import ensure_dir_permissions, ensure_file_permissions


class MappingStore:
    def write_mapping(
        self,
        *,
        case_id: str,
        schema_version: str,
        documents: list[dict[str, object]],
        output_root: Path,
        file_mode: int = 0o600,
        dir_mode: int = 0o700,
    ) -> Path:
        mapping_path = output_root / "mapping.json"
        ensure_dir_permissions(output_root, dir_mode)

        placeholder_to_value: dict[str, str] = {}
        for doc in documents:
            replacements = doc.get("replacements", {})
            if isinstance(replacements, dict):
                for original, placeholder in replacements.items():
                    placeholder_to_value[str(placeholder)] = str(original)

        payload = {
            "schema_version": schema_version,
            "case_id": case_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "placeholder_to_value": dict(sorted(placeholder_to_value.items())),
            "documents": documents,
        }
        mapping_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        ensure_file_permissions(mapping_path, file_mode)
        return mapping_path

    def read_mapping(self, mapping_path: Path) -> dict[str, object]:
        try:
            payload = json.loads(mapping_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InputValidationError("Mapping file unreadable") from exc
        if not isinstance(payload, dict):
            raise InputValidationError("Mapping file format invalid")
        return payload


def resolve_placeholder_reverse(payload: dict[str, object]) -> dict[str, str]:
    direct = payload.get("placeholder_to_value")
    if isinstance(direct, dict):
        return {str(k): str(v) for k, v in direct.items()}

    reverse: dict[str, str] = {}
    docs = payload.get("documents", [])
    if isinstance(docs, list):
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            replacements = doc.get("replacements", {})
            if not isinstance(replacements, dict):
                continue
            for original, placeholder in replacements.items():
                reverse[str(placeholder)] = str(original)
    return reverse
