from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.engines.base import EngineInitConfig
from src.models.backend_descriptor import BackendDescriptor, ReadinessCheckResult
from src.models.canonical_result import CanonicalAnonymizationResult, EntityReplacement, ProcessingMetadata
from src.models.mapping_artifact import MappingArtifact
from src.services.anonymization_service import AnonymizationService
from src.services.deanonymization_service import DeanonymizationService
from src.services.readiness_service import ReadinessError, ReadinessService


def _check(
    name: str,
    *,
    severity: str,
    status: str,
    message: str,
    remediation: str | None = None,
) -> ReadinessCheckResult:
    return ReadinessCheckResult(
        check_name=name,
        severity=severity,
        status=status,
        message=message,
        remediation=remediation,
    )


def _descriptor(engine_id: str, availability_status: str, checks: list[ReadinessCheckResult]) -> BackendDescriptor:
    return BackendDescriptor(
        engine_id=engine_id,
        display_name=f"{engine_id.title()} backend",
        availability_status=availability_status,  # type: ignore[arg-type]
        capabilities=["anonymize", "deanonymize"],
        readiness_checks=checks,
    )


class _StubWrapper:
    def __init__(self, engine_id: str) -> None:
        self.engine_id = engine_id

    def initialize(self, config: EngineInitConfig) -> BackendDescriptor:
        _ = config
        return _descriptor(
            self.engine_id,
            "ready",
            [
                _check(
                    "cpu_only_compatibility",
                    severity="critical",
                    status="pass",
                    message="CPU-only mode is supported and does not require GPU acceleration.",
                )
            ],
        )

    def anonymize(self, text: str, options: dict | None = None) -> CanonicalAnonymizationResult:
        _ = options
        return CanonicalAnonymizationResult(
            anonymized_text=text.replace("Alice", "<PER_1>"),
            mapping={"meta": {"device": -1}},
            entities=[
                EntityReplacement(
                    entity_type="PERSON",
                    source_value="Alice",
                    replacement_value="<PER_1>",
                )
            ],
            engine_id=self.engine_id,
            processing_metadata=ProcessingMetadata(request_id=f"req-{self.engine_id}", duration_ms=1, local_only_mode=True),
        )

    def deanonymize(self, anonymized_text: str, mapping_artifact: MappingArtifact) -> str:
        restored = anonymized_text
        for entry in mapping_artifact.entries:
            restored = restored.replace(entry.placeholder, entry.original_value)
        return restored

    def readiness_checks(self) -> list[ReadinessCheckResult]:
        return []


def test_unavailable_backend_is_blocked_with_remediation_but_ready_backend_runs(tmp_path: Path) -> None:
    readiness_service = ReadinessService(
        bootstrap_provider=lambda: [
            _descriptor(
                "classic",
                "unavailable",
                [
                    _check(
                        "transformers",
                        severity="critical",
                        status="fail",
                        message="missing",
                        remediation="Install missing module 'transformers' in the project environment and rerun readiness.",
                    ),
                    _check(
                        "cpu_only_compatibility",
                        severity="critical",
                        status="pass",
                        message="CPU-only mode is supported and does not require GPU acceleration.",
                    ),
                ],
            ),
            _descriptor(
                "transformer",
                "ready",
                [
                    _check(
                        "cpu_only_compatibility",
                        severity="critical",
                        status="pass",
                        message="CPU-only mode is supported and does not require GPU acceleration.",
                    )
                ],
            ),
        ]
    )
    service = AnonymizationService(
        wrappers={"classic": _StubWrapper("classic"), "transformer": _StubWrapper("transformer")},
        readiness_service=readiness_service,
    )
    input_path = tmp_path / "input.txt"
    input_path.write_text("Alice says hi", encoding="utf-8")

    with pytest.raises(ReadinessError) as exc_info:
        service.run(backend="classic", input_path=input_path)

    assert "Install missing module 'transformers'" in str(exc_info.value)
    transformer_job = service.run(backend="transformer", input_path=input_path)
    assert transformer_job.output_path.exists()
    assert transformer_job.mapping_path.exists()
    assert transformer_job.result.mapping["meta"]["device"] == -1


def test_deanonymization_fails_with_actionable_message_when_origin_model_is_missing(tmp_path: Path) -> None:
    readiness_service = ReadinessService(
        bootstrap_provider=lambda: [
            _descriptor(
                "classic",
                "ready",
                [
                    _check(
                        "cpu_only_compatibility",
                        severity="critical",
                        status="pass",
                        message="CPU-only mode is supported and does not require GPU acceleration.",
                    )
                ],
            ),
            _descriptor(
                "transformer",
                "unavailable",
                [
                    _check(
                        "urchade/gliner_multi_pii-v1",
                        severity="critical",
                        status="fail",
                        message="model missing",
                        remediation="Provision model assets for 'urchade/gliner_multi_pii-v1' before enabling this backend.",
                    )
                ],
            ),
        ]
    )
    service = DeanonymizationService(
        wrappers={"classic": _StubWrapper("classic"), "transformer": _StubWrapper("transformer")},
        readiness_service=readiness_service,
    )

    anonymized_input = tmp_path / "anon.txt"
    anonymized_input.write_text("<PER_1> says hi", encoding="utf-8")
    mapping_path = tmp_path / "mapping.json"
    mapping_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "mapping_format": "canonical-v1",
                "origin": {
                    "engine_id": "transformer",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "wrapper_contract_version": "1.0",
                },
                "entries": [
                    {
                        "placeholder": "<PER_1>",
                        "original_value": "Alice",
                        "entity_type": "PERSON",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ReadinessError) as exc_info:
        service.run(input_path=anonymized_input, mapping_path=mapping_path)

    assert "Provision model assets" in str(exc_info.value)

