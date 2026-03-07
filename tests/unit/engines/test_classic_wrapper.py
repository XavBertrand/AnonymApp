from __future__ import annotations

from pathlib import Path

import pytest

from src.engines.base import EngineInitConfig
from src.engines.classic_wrapper import ClassicWrapper


def _write_stub_engine(path: Path) -> None:
    path.write_text(
        """
class Settings:
    def __init__(self, device=123, enable_llm_qc=True):
        self.device = device
        self.enable_llm_qc = enable_llm_qc

def anonymize_text(raw_text, *, settings=None, **kwargs):
    return "<PER_1>", {
        "entities": [{"tag": "<PER_1>", "type": "PERSON", "canonical": "Alice", "mentions": ["Alice"]}],
        "meta": {"device": getattr(settings, "device", None), "enable_llm_qc": getattr(settings, "enable_llm_qc", None)},
    }

def deanonymize_text(anonymized_text, mapping, restore="canonical"):
    return anonymized_text.replace("<PER_1>", "Alice")
""".strip(),
        encoding="utf-8",
    )


def test_classic_wrapper_forces_cpu_mode_and_normalizes_result(tmp_path: Path) -> None:
    script_path = tmp_path / "anonymizer_stub.py"
    _write_stub_engine(script_path)

    wrapper = ClassicWrapper(script_path=script_path, module_name="anonymizer_cpu_stub")
    wrapper.initialize(EngineInitConfig(engine_id="classic", options={}))
    result = wrapper.anonymize("hello world")

    assert result.mapping["meta"]["device"] == -1
    assert result.engine_id == "classic"
    assert result.entities[0].entity_type == "PERSON"


def test_classic_wrapper_works_without_cuda_runtime(tmp_path: Path) -> None:
    script_path = tmp_path / "anonymizer_stub.py"
    _write_stub_engine(script_path)

    wrapper = ClassicWrapper(script_path=script_path, module_name="anonymizer_no_cuda_stub")
    descriptor = wrapper.initialize(EngineInitConfig(engine_id="classic", options={}))
    assert descriptor.availability_status == "ready"
    assert wrapper.anonymize("text").anonymized_text == "<PER_1>"


def test_classic_wrapper_reports_missing_script() -> None:
    wrapper = ClassicWrapper(script_path=Path("/tmp/does-not-exist-anonymizer.py"))
    with pytest.raises(RuntimeError):
        wrapper.initialize(EngineInitConfig(engine_id="classic", options={}))
