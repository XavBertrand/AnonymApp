from pathlib import Path

import pytest

from anonymizer_core.cli import main as anonymizer_main


@pytest.mark.acceptance
def test_us3_strict_offline_policy_is_enforced(tmp_path: Path) -> None:
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
            "CASE-US3-001",
            "--policy",
            "strict_offline",
            "--report",
            str(report),
        ]
    )
    assert exit_code == 0

    assert (tmp_path / "mapping.json").exists()
    assert (tmp_path / "report.json").exists()
