"""Policy loading/validation for offline standalone runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from anonymizer_core.errors import PolicyValidationError
from anonymizer_core.models import Policy
from anonymizer_core.schema import MAPPING_SCHEMA_VERSION, REPORT_SCHEMA_VERSION


STRICT_OFFLINE_POLICY_NAME = "strict_offline"


def _default_profiles() -> dict[str, Any]:
    return {
        "profiles": {
            STRICT_OFFLINE_POLICY_NAME: {
                "allow_network": False,
                "enable_ner": True,
                "enable_regex": True,
                "enable_rules": True,
                "continue_on_error": True,
                "emit_mapping": True,
                "mapping_required": True,
                "max_documents_per_batch": 500,
                "max_pages_per_document": 1000,
                "max_total_input_mb": 1024,
                "mapping_schema_version": MAPPING_SCHEMA_VERSION,
                "report_schema_version": REPORT_SCHEMA_VERSION,
                "storage_permissions_dir": "0700",
                "storage_permissions_file": "0600",
            }
        }
    }


def _parse_octal(value: Any, fallback: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        txt = value.strip()
        if txt.startswith("0"):
            return int(txt, 8)
        return int(txt)
    return fallback


def load_policy(policy_name: str, config_path: Path | None = None) -> Policy:
    data = _default_profiles()
    if config_path and config_path.exists():
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if isinstance(loaded, dict):
            data = loaded

    profiles = data.get("profiles") if isinstance(data, dict) else None
    if not isinstance(profiles, dict) or policy_name not in profiles:
        raise PolicyValidationError(f"Unknown policy profile: {policy_name}")

    raw = profiles[policy_name]
    if not isinstance(raw, dict):
        raise PolicyValidationError("Policy profile must be a mapping")

    if not any(bool(raw.get(name, False)) for name in ("enable_ner", "enable_regex", "enable_rules")):
        raise PolicyValidationError("At least one detector path must be enabled")

    policy = Policy(
        policy_id=policy_name,
        allow_network=bool(raw.get("allow_network", False)),
        enable_ner=bool(raw.get("enable_ner", True)),
        enable_regex=bool(raw.get("enable_regex", True)),
        enable_rules=bool(raw.get("enable_rules", True)),
        continue_on_error=bool(raw.get("continue_on_error", True)),
        emit_mapping=bool(raw.get("emit_mapping", True)),
        mapping_required=bool(raw.get("mapping_required", True)),
        max_documents_per_batch=int(raw.get("max_documents_per_batch", 500)),
        max_pages_per_document=int(raw.get("max_pages_per_document", 1000)),
        max_total_input_mb=int(raw.get("max_total_input_mb", 1024)),
        mapping_schema_version=str(raw.get("mapping_schema_version", MAPPING_SCHEMA_VERSION)),
        report_schema_version=str(raw.get("report_schema_version", REPORT_SCHEMA_VERSION)),
        storage_permissions_dir=_parse_octal(raw.get("storage_permissions_dir", "0700"), 0o700),
        storage_permissions_file=_parse_octal(raw.get("storage_permissions_file", "0600"), 0o600),
    )

    if policy.allow_network:
        raise PolicyValidationError("Standalone mode forbids network-enabled policies")
    return policy
