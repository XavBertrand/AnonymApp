from pathlib import Path
import json

import pytest

from anonymizer_core.cli import main as anonymizer_main


@pytest.mark.acceptance
def test_us2_mapping_clear_json_and_deanonymize_roundtrip(tmp_path: Path) -> None:
    sample = Path("tests/data/anonymization/fixtures/us1/sample.txt")
    report = tmp_path / "report.json"

    exit_code = anonymizer_main(
        [
            "anonymize",
            "--input",
            str(sample),
            "--output",
            str(tmp_path),
            "--case-id",
            "CASE-US2-001",
            "--report",
            str(report),
        ]
    )
    assert exit_code == 0

    mapping_path = tmp_path / "mapping.json"
    mapping_payload = json.loads(mapping_path.read_text(encoding="utf-8"))
    reverse = mapping_payload["placeholder_to_value"]
    assert isinstance(reverse, dict)
    assert reverse

    anon_file = tmp_path / "anonymized_txt" / "sample_txt.txt"
    restored = tmp_path / "restored.txt"
    exit_de = anonymizer_main(
        [
            "deanonymize",
            "--mapping",
            str(mapping_path),
            "--text-file",
            str(anon_file),
            "--output",
            str(restored),
        ]
    )
    assert exit_de == 0

    restored_text = restored.read_text(encoding="utf-8")
    assert "Alice Martin" in restored_text
    assert "alice.martin@example.com" in restored_text
