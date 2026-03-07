from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from src.config.settings import MAPPINGS_DIR, OUTPUTS_DIR
from src.engines.classic_wrapper import ClassicWrapper
from src.engines.transformer_wrapper import TransformerWrapper
from src.services.anonymization_service import AnonymizationService


def _write_stub_engine(path: Path) -> None:
    path.write_text(
        """
class Settings:
    def __init__(self, device=42, enable_llm_qc=True):
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
                "score": 0.88,
            }
        },
        "meta": {"device": device, "model_name": model_name},
    }
""".strip(),
        encoding="utf-8",
    )


def test_backend_a_txt_anonymization_exports_runtime_files_and_forces_cpu(tmp_path: Path) -> None:
    script_path = tmp_path / "anonymizer_stub.py"
    _write_stub_engine(script_path)

    wrapper = ClassicWrapper(script_path=script_path, module_name=f"anonymizer_integration_{uuid4().hex}")
    service = AnonymizationService(wrappers={"classic": wrapper})

    input_path = tmp_path / "sample.txt"
    input_path.write_text("Alice says hi", encoding="utf-8")

    job = service.run(backend="classic", input_path=input_path)

    assert OUTPUTS_DIR in job.output_path.parents
    assert MAPPINGS_DIR in job.mapping_path.parents
    assert job.output_path.exists()
    assert job.mapping_path.exists()
    assert job.output_path.read_text(encoding="utf-8") == "<PER_1> says hi"

    mapping_payload = json.loads(job.mapping_path.read_text(encoding="utf-8"))
    assert mapping_payload["origin"]["engine_id"] == "classic"
    assert mapping_payload["mapping_format"] == "canonical-v1"

    # Wrapper enforces CPU-only regardless of environment/CUDA availability.
    assert job.result.mapping["meta"]["device"] == -1


def test_backend_selection_supports_classic_and_transformer_with_same_runtime_behavior(tmp_path: Path) -> None:
    classic_script = tmp_path / "anonymizer.py"
    transformer_script = tmp_path / "transformer_anonymizer.py"
    _write_stub_engine(classic_script)
    _write_transformer_stub(transformer_script)

    classic_wrapper = ClassicWrapper(script_path=classic_script, module_name=f"anonymizer_select_{uuid4().hex}")
    transformer_wrapper = TransformerWrapper(
        script_path=transformer_script,
        classic_script_path=classic_script,
        module_name=f"transformer_select_{uuid4().hex}",
    )
    service = AnonymizationService(wrappers={"classic": classic_wrapper, "transformer": transformer_wrapper})

    input_path = tmp_path / "sample.txt"
    input_path.write_text("Alice says hi", encoding="utf-8")

    classic_job = service.run(backend="classic", input_path=input_path)
    transformer_job = service.run(backend="transformer", input_path=input_path)

    assert classic_job.output_path.exists()
    assert transformer_job.output_path.exists()
    assert OUTPUTS_DIR in classic_job.output_path.parents
    assert OUTPUTS_DIR in transformer_job.output_path.parents
    assert MAPPINGS_DIR in classic_job.mapping_path.parents
    assert MAPPINGS_DIR in transformer_job.mapping_path.parents
    assert classic_job.result.engine_id == "classic"
    assert transformer_job.result.engine_id == "transformer"
