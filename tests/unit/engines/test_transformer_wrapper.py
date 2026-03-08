from __future__ import annotations

from pathlib import Path

import pytest

from src.engines.base import EngineInitConfig
from src.engines.transformer_wrapper import TransformerWrapper


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


def test_transformer_wrapper_forces_cpu_and_normalizes_result(tmp_path: Path) -> None:
    classic_script = tmp_path / "anonymizer.py"
    transformer_script = tmp_path / "transformer_anonymizer.py"
    _write_classic_stub(classic_script)
    _write_transformer_stub(transformer_script)

    wrapper = TransformerWrapper(
        script_path=transformer_script,
        classic_script_path=classic_script,
        module_name="transformer_wrapper_cpu_stub",
    )
    wrapper.initialize(EngineInitConfig(engine_id="transformer", options={}))
    result = wrapper.anonymize("Alice says hi")

    assert result.engine_id == "transformer"
    assert result.anonymized_text == "<PERSON_1> says hi"
    assert result.mapping["meta"]["device"] == -1
    assert len(result.entities) == 1
    assert result.entities[0].entity_type == "PERSON"


def test_transformer_wrapper_works_without_cuda_runtime(tmp_path: Path) -> None:
    classic_script = tmp_path / "anonymizer.py"
    transformer_script = tmp_path / "transformer_anonymizer.py"
    _write_classic_stub(classic_script)
    _write_transformer_stub(transformer_script)

    wrapper = TransformerWrapper(
        script_path=transformer_script,
        classic_script_path=classic_script,
        module_name="transformer_wrapper_no_cuda_stub",
    )
    descriptor = wrapper.initialize(EngineInitConfig(engine_id="transformer", options={}))
    assert descriptor.availability_status == "ready"
    assert wrapper.anonymize("x").mapping["meta"]["device"] == -1


def test_transformer_wrapper_reports_missing_script(tmp_path: Path) -> None:
    missing_script = tmp_path / "missing-transformer.py"
    wrapper = TransformerWrapper(script_path=missing_script)

    descriptor = wrapper.initialize(EngineInitConfig(engine_id="transformer", options={}))
    assert descriptor.availability_status == "unavailable"
    assert any(check.check_name == "script_load" and check.status == "fail" for check in descriptor.readiness_checks)

    with pytest.raises(RuntimeError):
        wrapper.anonymize("text")


def test_transformer_and_classic_parity_on_canonical_fields(tmp_path: Path) -> None:
    from src.engines.classic_wrapper import ClassicWrapper

    classic_script = tmp_path / "anonymizer.py"
    transformer_script = tmp_path / "transformer_anonymizer.py"
    _write_classic_stub(classic_script)
    _write_transformer_stub(transformer_script)

    classic = ClassicWrapper(script_path=classic_script, module_name="parity_classic_stub")
    transformer = TransformerWrapper(
        script_path=transformer_script,
        classic_script_path=classic_script,
        module_name="parity_transformer_stub",
        classic_module_name="anonymizer",
    )

    classic.initialize(EngineInitConfig(engine_id="classic", options={}))
    transformer.initialize(EngineInitConfig(engine_id="transformer", options={}))
    classic_result = classic.anonymize("Alice says hi")
    transformer_result = transformer.anonymize("Alice says hi")

    for result in (classic_result, transformer_result):
        assert result.anonymized_text
        assert result.mapping is not None
        assert isinstance(result.entities, list)
        assert result.processing_metadata.local_only_mode is True
