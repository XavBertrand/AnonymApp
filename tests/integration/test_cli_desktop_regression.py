from __future__ import annotations

from pathlib import Path

from src.app.cli.main import build_parser, main
from src.models.canonical_result import CanonicalAnonymizationResult, ProcessingMetadata
from src.services.anonymization_service import AnonymizationJobResult


def test_cli_commands_remain_available() -> None:
    parser = build_parser()

    commands = parser._subparsers._group_actions[0].choices.keys()

    assert {"anonymize", "deanonymize", "readiness"}.issubset(commands)


def test_cli_anonymize_entrypoint_remains_unchanged(monkeypatch, tmp_path: Path) -> None:
    input_path = tmp_path / "input.txt"
    input_path.write_text("Alice", encoding="utf-8")

    def _fake_run_job(*, backend: str, input_path: Path, output_path: Path | None = None, mapping_path: Path | None = None) -> AnonymizationJobResult:
        resolved_output = output_path or (tmp_path / "output.txt")
        resolved_mapping = mapping_path or (tmp_path / "mapping.json")
        resolved_output.write_text("anon", encoding="utf-8")
        resolved_mapping.write_text("{}", encoding="utf-8")
        return AnonymizationJobResult(
            result=CanonicalAnonymizationResult(
                anonymized_text="anon",
                mapping={},
                entities=[],
                engine_id=backend,
                processing_metadata=ProcessingMetadata(request_id="req", duration_ms=1),
            ),
            output_path=resolved_output,
            mapping_path=resolved_mapping,
        )

    monkeypatch.setattr("src.services.anonymization_service.run_anonymization_job", _fake_run_job)

    assert main(["anonymize", "--input", str(input_path)]) == 0
