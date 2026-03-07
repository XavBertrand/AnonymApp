from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from src.adapters.mappings.canonical_mapping_adapter import MappingCompatibilityError
from src.engines.classic_wrapper import ClassicWrapper
from src.engines.transformer_wrapper import TransformerWrapper
from src.services.anonymization_service import AnonymizationService
from src.services.deanonymization_service import DeanonymizationService


def _write_classic_stub(path: Path) -> None:
    path.write_text(
        """
import re
DATE_RE = re.compile(r".*")
EMAIL_RE = re.compile(r".*")
IBAN_RE = re.compile(r".*")
PHONE_RE = re.compile(r".*")
SIREN_SIRET_RE = re.compile(r".*")

class Settings:
    def __init__(self, device=0, enable_llm_qc=True):
        self.device = device
        self.enable_llm_qc = enable_llm_qc

def anonymize_text(raw_text, *, settings=None, **kwargs):
    return "<PER_1> says hi", {
        "entities": [
            {"tag": "<PER_1>", "type": "PERSON", "canonical": "Alice", "mentions": ["Alice"]}
        ],
        "summary": {"PERSON": 1},
        "meta": {"device": getattr(settings, "device", None)}
    }

def deanonymize_text(anonymized_text, mapping, restore="canonical"):
    return anonymized_text.replace("<PER_1>", "Alice")
""".strip(),
        encoding="utf-8",
    )


def _write_transformer_stub(path: Path) -> None:
    path.write_text(
        """
from anonymizer import DATE_RE, EMAIL_RE, IBAN_RE, PHONE_RE, SIREN_SIRET_RE

def run_transformer_anonymization(text, *, model_name="stub", device="cuda", **kwargs):
    _ = (DATE_RE, EMAIL_RE, IBAN_RE, PHONE_RE, SIREN_SIRET_RE)
    return "<PERSON_1> says hi", {
        "entities": {
            "<PERSON_1>": {
                "label": "PERSON",
                "canonical": "Alice",
                "values": ["Alice"],
                "score": 0.91,
            }
        },
        "meta": {"device": device, "model_name": model_name},
    }
""".strip(),
        encoding="utf-8",
    )


def _build_services(tmp_path: Path) -> tuple[AnonymizationService, DeanonymizationService]:
    classic_script = tmp_path / "anonymizer.py"
    transformer_script = tmp_path / "transformer_anonymizer.py"
    _write_classic_stub(classic_script)
    _write_transformer_stub(transformer_script)

    classic_wrapper = ClassicWrapper(script_path=classic_script, module_name=f"classic_map_{uuid4().hex}")
    transformer_wrapper = TransformerWrapper(
        script_path=transformer_script,
        classic_script_path=classic_script,
        module_name=f"transformer_map_{uuid4().hex}",
        classic_module_name="anonymizer",
    )
    wrappers = {"classic": classic_wrapper, "transformer": transformer_wrapper}
    return AnonymizationService(wrappers=wrappers), DeanonymizationService(wrappers=wrappers)


def test_mapping_export_import_roundtrip_and_successful_deanonymization(tmp_path: Path) -> None:
    anonymization_service, deanonymization_service = _build_services(tmp_path)

    input_path = tmp_path / "roundtrip.txt"
    input_path.write_text("Alice says hi", encoding="utf-8")

    anonymized_job = anonymization_service.run(backend="classic", input_path=input_path)
    deanonymized_job = deanonymization_service.run(
        input_path=anonymized_job.output_path,
        mapping_path=anonymized_job.mapping_path,
    )

    assert deanonymized_job.engine_id == "classic"
    assert deanonymized_job.deanonymized_text == "Alice says hi"
    assert deanonymized_job.output_path.exists()


def test_incompatible_mapping_failure_unsupported_schema(tmp_path: Path) -> None:
    _, deanonymization_service = _build_services(tmp_path)

    anonymized_input = tmp_path / "anon.txt"
    anonymized_input.write_text("<PER_1> says hi", encoding="utf-8")

    bad_mapping = tmp_path / "bad.mapping.json"
    bad_mapping.write_text(
        json.dumps(
            {
                "schema_version": "99.0",
                "mapping_format": "canonical-v1",
                "origin": {
                    "engine_id": "classic",
                    "generated_at": "2026-03-07T10:00:00+00:00",
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

    with pytest.raises(MappingCompatibilityError) as exc_info:
        deanonymization_service.run(input_path=anonymized_input, mapping_path=bad_mapping)

    assert exc_info.value.category == "unsupported_schema_version"
    assert "Remediation:" in str(exc_info.value)


def test_deanonymization_routes_to_origin_backend(tmp_path: Path) -> None:
    anonymization_service, deanonymization_service = _build_services(tmp_path)

    input_path = tmp_path / "route.txt"
    input_path.write_text("Alice says hi", encoding="utf-8")

    transformer_job = anonymization_service.run(backend="transformer", input_path=input_path)
    deanonymized_job = deanonymization_service.run(
        input_path=transformer_job.output_path,
        mapping_path=transformer_job.mapping_path,
    )

    assert deanonymized_job.engine_id == "transformer"
    assert deanonymized_job.deanonymized_text == "Alice says hi"


def test_invalid_mapping_file_fails_gracefully(tmp_path: Path) -> None:
    _, deanonymization_service = _build_services(tmp_path)

    anonymized_input = tmp_path / "anon-invalid.txt"
    anonymized_input.write_text("<PER_1> says hi", encoding="utf-8")

    invalid_mapping = tmp_path / "invalid.mapping.json"
    invalid_mapping.write_text("{not-json", encoding="utf-8")

    with pytest.raises(MappingCompatibilityError) as exc_info:
        deanonymization_service.run(input_path=anonymized_input, mapping_path=invalid_mapping)

    assert exc_info.value.category == "invalid_mapping_file"
