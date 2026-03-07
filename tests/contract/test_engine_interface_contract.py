from __future__ import annotations

from pathlib import Path

from src.engines.base import EngineInitConfig
from src.engines.classic_wrapper import ClassicWrapper
from src.engines.transformer_wrapper import TransformerWrapper
from src.models.canonical_result import CanonicalAnonymizationResult
from src.models.mapping_artifact import MappingArtifact, MappingEntry, MappingOrigin


def _write_stub_engine(path: Path) -> None:
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
        "meta": {"device": getattr(settings, "device", None)},
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


def test_classic_wrapper_implements_engine_contract(tmp_path: Path) -> None:
    script_path = tmp_path / "anonymizer_stub.py"
    _write_stub_engine(script_path)

    wrapper = ClassicWrapper(script_path=script_path, module_name="anonymizer_contract_stub")
    descriptor = wrapper.initialize(EngineInitConfig(engine_id="classic", options={}))
    assert descriptor.engine_id == "classic"

    result = wrapper.anonymize("hello world")
    assert isinstance(result, CanonicalAnonymizationResult)
    assert result.engine_id == "classic"
    assert result.anonymized_text
    assert result.mapping

    mapping = MappingArtifact(
        schema_version="1.0",
        mapping_format="canonical-v1",
        origin=MappingOrigin(engine_id="classic"),
        entries=[MappingEntry(placeholder="<PER_1>", original_value="Alice", entity_type="PERSON")],
    )
    restored = wrapper.deanonymize("<PER_1> says hi", mapping)
    assert restored == "Alice says hi"


def test_wrapper_contract_parity_for_classic_and_transformer(tmp_path: Path) -> None:
    classic_script = tmp_path / "anonymizer.py"
    transformer_script = tmp_path / "transformer_anonymizer.py"
    _write_stub_engine(classic_script)
    _write_transformer_stub(transformer_script)

    classic = ClassicWrapper(script_path=classic_script, module_name="contract_classic")
    transformer = TransformerWrapper(
        script_path=transformer_script,
        classic_script_path=classic_script,
        module_name="contract_transformer",
        classic_module_name="anonymizer",
    )

    wrappers = {
        "classic": classic,
        "transformer": transformer,
    }

    for engine_id, wrapper in wrappers.items():
        descriptor = wrapper.initialize(EngineInitConfig(engine_id=engine_id, options={}))
        assert descriptor.engine_id == engine_id
        assert descriptor.availability_status == "ready"

        result = wrapper.anonymize("Alice says hi")
        assert isinstance(result, CanonicalAnonymizationResult)
        assert result.engine_id == engine_id
        assert isinstance(result.anonymized_text, str) and result.anonymized_text
        assert isinstance(result.mapping, dict)
        assert isinstance(result.entities, list)
        assert result.processing_metadata.local_only_mode is True
        assert result.processing_metadata.duration_ms >= 0

    common_fields = {
        "anonymized_text",
        "mapping",
        "entities",
        "engine_id",
        "processing_metadata",
        "pseudonym_metadata",
    }
    assert common_fields.issubset(set(CanonicalAnonymizationResult.__dataclass_fields__.keys()))
