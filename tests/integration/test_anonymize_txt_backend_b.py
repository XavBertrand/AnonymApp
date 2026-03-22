from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from src.app.cli.main import main
from src.engines.classic_wrapper import ClassicWrapper
from src.engines.transformer_wrapper import TransformerWrapper
from src.models.canonical_result import (
    CanonicalAnonymizationResult,
    ProcessingMetadata,
)
from src.services.anonymization_service import AnonymizationJobResult, AnonymizationService


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
    def __init__(self, device=42, enable_llm_qc=True):
        self.device = device
        self.enable_llm_qc = enable_llm_qc

def anonymize_text(raw_text, *, settings=None, **kwargs):
    return "<PER_1> says hi", {
        "entities": [
            {"tag": "<PER_1>", "type": "PERSON", "canonical": "Alice", "mentions": ["Alice"]}
        ],
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
                "score": 0.88,
            }
        },
        "meta": {"device": device, "model_name": model_name},
    }
""".strip(),
        encoding="utf-8",
    )


def test_cli_uses_transformer_only_flow(monkeypatch, tmp_path: Path) -> None:
    input_path = tmp_path / "input.txt"
    input_path.write_text("Alice says hi", encoding="utf-8")

    captured_backends: list[str] = []

    def _fake_run_job(*, backend: str, input_path: Path, output_path: Path | None = None, mapping_path: Path | None = None) -> AnonymizationJobResult:
        captured_backends.append(backend)
        resolved_output = output_path or (tmp_path / f"{backend}.anon.txt")
        resolved_mapping = mapping_path or (tmp_path / f"{backend}.mapping.json")
        resolved_output.write_text(f"{backend}-anonymized", encoding="utf-8")
        resolved_mapping.write_text("{}", encoding="utf-8")

        result = CanonicalAnonymizationResult(
            anonymized_text=f"{backend}-anonymized",
            mapping={"meta": {"device": -1}},
            entities=[],
            engine_id=backend,
            processing_metadata=ProcessingMetadata(request_id=f"req-{backend}", duration_ms=1),
        )
        return AnonymizationJobResult(result=result, output_path=resolved_output, mapping_path=resolved_mapping)

    monkeypatch.setattr("src.services.anonymization_service.run_anonymization_job", _fake_run_job)

    assert main(["anonymize", "--input", str(input_path)]) == 0
    assert main(["anonymize", "--engine", "transformer", "--input", str(input_path)]) == 0
    with pytest.raises(SystemExit):
        main(["anonymize", "--engine", "classic", "--input", str(input_path)])
    assert captured_backends == ["transformer", "transformer"]


def test_backend_b_switching_keeps_cpu_only_initialization(tmp_path: Path) -> None:
    classic_script = tmp_path / "anonymizer.py"
    transformer_script = tmp_path / "transformer_anonymizer.py"
    _write_classic_stub(classic_script)
    _write_transformer_stub(transformer_script)

    classic_wrapper = ClassicWrapper(script_path=classic_script, module_name=f"classic_b_{uuid4().hex}")
    transformer_wrapper = TransformerWrapper(
        script_path=transformer_script,
        classic_script_path=classic_script,
        module_name=f"transformer_b_{uuid4().hex}",
        classic_module_name="anonymizer",
    )
    service = AnonymizationService(wrappers={"classic": classic_wrapper, "transformer": transformer_wrapper})

    input_path = tmp_path / "sample.txt"
    input_path.write_text("Alice says hi", encoding="utf-8")

    classic_job = service.run(backend="classic", input_path=input_path)
    transformer_job = service.run(backend="transformer", input_path=input_path)

    assert classic_job.result.mapping["meta"]["device"] == -1
    assert transformer_job.result.mapping["meta"]["device"] == -1
