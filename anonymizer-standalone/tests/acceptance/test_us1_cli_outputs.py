from pathlib import Path
import json

import pytest

from anonymizer_core.cli import main as anonymizer_main


@pytest.mark.acceptance
def test_us1_batch_multiformat_outputs_flat_txt(tmp_path: Path) -> None:
    fixtures = Path("tests/data/anonymization/fixtures/us1")
    report = tmp_path / "report.json"

    exit_code = anonymizer_main(
        [
            "anonymize",
            "--input",
            str(fixtures),
            "--output",
            str(tmp_path),
            "--case-id",
            "CASE-US1-001",
            "--report",
            str(report),
            "--concat",
        ]
    )
    assert exit_code == 0

    out_root = tmp_path / "anonymized_txt"
    assert (out_root / "sample_txt.txt").exists()
    assert (out_root / "sample_pdf.txt").exists()
    assert (out_root / "sample_docx.txt").exists()
    assert (out_root / "sample_xlsx.txt").exists()

    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["totals"]["total_documents"] == 4
    assert payload["totals"]["failed"] == 0

    mapping_path = tmp_path / "mapping.json"
    assert mapping_path.exists()
    concat_path = tmp_path / "anonymized_all.txt"
    assert concat_path.exists()
