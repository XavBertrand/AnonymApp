from __future__ import annotations

import importlib.util
import logging
import sys
import time
from pathlib import Path
from types import ModuleType
from uuid import uuid4

from src.config.logging import translate_error
from src.config.settings import TMP_CLASSIC_SCRIPT
from src.engines.base import EngineInitConfig
from src.models.backend_descriptor import BackendDescriptor, ReadinessCheckResult
from src.models.canonical_result import (
    CanonicalAnonymizationResult,
    EntityReplacement,
    ProcessingMetadata,
)
from src.models.mapping_artifact import MappingArtifact

LOGGER = logging.getLogger(__name__)


class ClassicWrapper:
    engine_id = "classic"

    def __init__(self, script_path: Path | None = None, module_name: str = "anonymizer") -> None:
        self._script_path = script_path or TMP_CLASSIC_SCRIPT
        self._module_name = module_name
        self._module: ModuleType | None = None
        self._init_config: EngineInitConfig | None = None

    def _load_module(self) -> ModuleType:
        if not self._script_path.exists():
            raise RuntimeError(f"Classic backend script not found: {self._script_path}")

        spec = importlib.util.spec_from_file_location(self._module_name, self._script_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to build module spec from {self._script_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[self._module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            raise RuntimeError(f"Classic backend loading failed: {translate_error(exc)}") from exc
        return module

    def _ensure_loaded(self) -> ModuleType:
        if self._module is None:
            self._module = self._load_module()
        return self._module

    @staticmethod
    def _to_check(name: str, ok: bool, required: bool = True, remediation: str | None = None) -> ReadinessCheckResult:
        return ReadinessCheckResult(
            check_name=name,
            severity="critical" if required else "warning",
            status="pass" if ok else "fail",
            message="available" if ok else "missing",
            remediation=remediation if not ok else None,
        )

    def initialize(self, config: EngineInitConfig) -> BackendDescriptor:
        self._init_config = config
        checks: list[ReadinessCheckResult] = []
        try:
            module = self._ensure_loaded()
            checks.append(self._to_check("script_load", True))
            checks.append(self._to_check("anonymize_text", callable(getattr(module, "anonymize_text", None))))
            checks.append(self._to_check("deanonymize_text", callable(getattr(module, "deanonymize_text", None))))
            checks.append(self._to_check("Settings", hasattr(module, "Settings")))
        except Exception as exc:
            checks.append(
                self._to_check(
                    "script_load",
                    False,
                    remediation=translate_error(exc),
                )
            )

        has_critical_failure = any(c.severity == "critical" and c.status == "fail" for c in checks)
        status = "unavailable" if has_critical_failure else "ready"
        return BackendDescriptor(
            engine_id=self.engine_id,
            display_name="Classic HF+Regex",
            availability_status=status,
            capabilities=["anonymize", "deanonymize"],
            readiness_checks=checks,
        )

    def _build_settings(self, options: dict | None = None) -> object | None:
        module = self._ensure_loaded()
        settings_cls = getattr(module, "Settings", None)
        if settings_cls is None:
            return None

        opts = dict(options or {})
        # Explicit CPU-only policy for all wrapper-invoked inference.
        opts["device"] = -1
        opts.setdefault("enable_llm_qc", False)

        try:
            return settings_cls(**opts)
        except TypeError:
            settings = settings_cls()
            if hasattr(settings, "device"):
                settings.device = -1
            if hasattr(settings, "enable_llm_qc"):
                settings.enable_llm_qc = bool(opts.get("enable_llm_qc", False))
            return settings

    @staticmethod
    def _normalize_entities(mapping: dict) -> list[EntityReplacement]:
        entities: list[EntityReplacement] = []
        for item in mapping.get("entities", []):
            tag = str(item.get("tag", "")).strip()
            canonical = str(item.get("canonical", "")).strip()
            mentions = item.get("mentions") or []
            source_value = str(mentions[0]).strip() if mentions else canonical
            entities.append(
                EntityReplacement(
                    entity_type=str(item.get("type", "UNKNOWN")).strip() or "UNKNOWN",
                    source_value=source_value,
                    replacement_value=tag or canonical,
                    confidence=item.get("score_avg"),
                )
            )
        return entities

    def anonymize(self, text: str, options: dict[str, object] | None = None) -> CanonicalAnonymizationResult:
        module = self._ensure_loaded()
        anonymize_text = getattr(module, "anonymize_text", None)
        if not callable(anonymize_text):
            raise RuntimeError("Classic backend does not expose callable anonymize_text")

        start = time.perf_counter()
        settings = self._build_settings((options or {}))
        try:
            anonymized_text, mapping = anonymize_text(text, settings=settings)
        except Exception as exc:
            raise RuntimeError(f"Classic anonymization failed: {translate_error(exc)}") from exc

        duration_ms = int((time.perf_counter() - start) * 1000)
        canonical = CanonicalAnonymizationResult(
            anonymized_text=anonymized_text,
            mapping=mapping if isinstance(mapping, dict) else {},
            entities=self._normalize_entities(mapping if isinstance(mapping, dict) else {}),
            engine_id=self.engine_id,
            processing_metadata=ProcessingMetadata(
                request_id=str(uuid4()),
                duration_ms=duration_ms,
                local_only_mode=True,
            ),
            pseudonym_metadata=(mapping or {}).get("pseudonym_map") if isinstance(mapping, dict) else None,
        )
        canonical.validate()
        return canonical

    @staticmethod
    def _mapping_artifact_to_dict(mapping_artifact: MappingArtifact) -> dict:
        entities = [
            {
                "tag": entry.placeholder,
                "type": entry.entity_type,
                "canonical": entry.original_value,
                "mentions": [entry.original_value],
            }
            for entry in mapping_artifact.entries
        ]
        return {"entities": entities}

    def deanonymize(self, anonymized_text: str, mapping_artifact: MappingArtifact) -> str:
        module = self._ensure_loaded()
        deanonymize_text = getattr(module, "deanonymize_text", None)
        if not callable(deanonymize_text):
            raise RuntimeError("Classic backend does not expose callable deanonymize_text")

        mapping = self._mapping_artifact_to_dict(mapping_artifact)
        try:
            return str(deanonymize_text(anonymized_text, mapping))
        except Exception as exc:
            raise RuntimeError(f"Classic deanonymization failed: {translate_error(exc)}") from exc

    def readiness_checks(self) -> list[ReadinessCheckResult]:
        descriptor = self.initialize(
            self._init_config or EngineInitConfig(engine_id=self.engine_id, options={})
        )
        return descriptor.readiness_checks
