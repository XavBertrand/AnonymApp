from __future__ import annotations

from pathlib import Path

from src.engines.base import EngineInitConfig
from src.engines.classic_wrapper import ClassicWrapper
from src.models.canonical_result import CanonicalAnonymizationResult
from src.models.mapping_artifact import MappingArtifact, MappingEntry, MappingOrigin


def _write_stub_engine(path: Path) -> None:
    path.write_text(
        """
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
