from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path
from types import ModuleType
from uuid import uuid4

from src.config.logging import translate_error
from src.config.settings import TMP_CLASSIC_SCRIPT, TMP_TRANSFORMER_SCRIPT
from src.engines.base import EngineInitConfig
from src.models.backend_descriptor import BackendDescriptor, ReadinessCheckResult
from src.models.canonical_result import (
    CanonicalAnonymizationResult,
    EntityReplacement,
    ProcessingMetadata,
)
from src.models.mapping_artifact import MappingArtifact


class TransformerWrapper:
    engine_id = "transformer"

    def __init__(
        self,
        script_path: Path | None = None,
        classic_script_path: Path | None = None,
        module_name: str = "transformer_anonymizer",
        classic_module_name: str = "anonymizer",
    ) -> None:
        self._script_path = script_path or TMP_TRANSFORMER_SCRIPT
        self._classic_script_path = classic_script_path or TMP_CLASSIC_SCRIPT
        self._module_name = module_name
        self._classic_module_name = classic_module_name
        self._module: ModuleType | None = None
        self._init_config: EngineInitConfig | None = None

    @staticmethod
    def _load_module_from_path(module_name: str, script_path: Path) -> ModuleType:
        spec = importlib.util.spec_from_file_location(module_name, script_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to build module spec from {script_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def _load_module(self) -> ModuleType:
        if not self._script_path.exists():
            raise RuntimeError(f"Transformer backend script not found: {self._script_path}")
        if not self._classic_script_path.exists():
            raise RuntimeError(f"Classic dependency script not found: {self._classic_script_path}")

        try:
            # Ensure `from anonymizer import ...` inside transformer script resolves deterministically.
            if self._classic_module_name not in sys.modules:
                self._load_module_from_path(self._classic_module_name, self._classic_script_path)

            return self._load_module_from_path(self._module_name, self._script_path)
        except Exception as exc:
            raise RuntimeError(f"Transformer backend loading failed: {translate_error(exc)}") from exc

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
            checks.append(
                self._to_check(
                    "run_transformer_anonymization",
                    callable(getattr(module, "run_transformer_anonymization", None)),
                )
            )
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
            display_name="Transformer GLiNER",
            availability_status=status,
            capabilities=["anonymize", "deanonymize"],
            readiness_checks=checks,
        )

    @staticmethod
    def _normalize_entities(mapping: dict) -> list[EntityReplacement]:
        entities: list[EntityReplacement] = []
        raw_entities = mapping.get("entities", [])

        if isinstance(raw_entities, dict):
            iterator = raw_entities.items()
            for placeholder, info in iterator:
                if not isinstance(info, dict):
                    continue
                canonical = str(
                    info.get("canonical")
                    or ((info.get("values") or [None])[0] or "")
                ).strip()
                entities.append(
                    EntityReplacement(
                        entity_type=str(info.get("label", info.get("type", "UNKNOWN"))).strip() or "UNKNOWN",
                        source_value=canonical or str(placeholder),
                        replacement_value=str(placeholder),
                        confidence=info.get("score"),
                    )
                )
            return entities

        if isinstance(raw_entities, list):
            for item in raw_entities:
                if not isinstance(item, dict):
                    continue
                tag = str(item.get("tag", "")).strip()
                canonical = str(item.get("canonical", "")).strip()
                mentions = item.get("mentions") or item.get("values") or []
                source_value = str(mentions[0]).strip() if mentions else canonical
                entities.append(
                    EntityReplacement(
                        entity_type=str(item.get("type", item.get("label", "UNKNOWN"))).strip() or "UNKNOWN",
                        source_value=source_value,
                        replacement_value=tag or canonical,
                        confidence=item.get("score_avg", item.get("score")),
                    )
                )
        return entities

    def anonymize(self, text: str, options: dict[str, object] | None = None) -> CanonicalAnonymizationResult:
        module = self._ensure_loaded()
        run_transformer_anonymization = getattr(module, "run_transformer_anonymization", None)
        if not callable(run_transformer_anonymization):
            raise RuntimeError("Transformer backend does not expose callable run_transformer_anonymization")

        opts = dict(options or {})
        # Enforce CPU-only execution regardless of machine GPU libraries.
        opts["device"] = -1

        start = time.perf_counter()
        try:
            anonymized_text, mapping = run_transformer_anonymization(text, **opts)
        except Exception as exc:
            raise RuntimeError(f"Transformer anonymization failed: {translate_error(exc)}") from exc

        if isinstance(mapping, dict):
            mapping.setdefault("meta", {})
            if isinstance(mapping["meta"], dict):
                mapping["meta"]["device"] = -1

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

    def deanonymize(self, anonymized_text: str, mapping_artifact: MappingArtifact) -> str:
        restored = anonymized_text
        # MappingArtifact is canonical; deanonymization here is deterministic replacement.
        for entry in sorted(mapping_artifact.entries, key=lambda e: len(e.placeholder), reverse=True):
            if entry.placeholder:
                restored = restored.replace(entry.placeholder, entry.original_value)
        return restored

    def readiness_checks(self) -> list[ReadinessCheckResult]:
        descriptor = self.initialize(
            self._init_config or EngineInitConfig(engine_id=self.engine_id, options={})
        )
        return descriptor.readiness_checks
