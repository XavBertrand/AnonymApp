from __future__ import annotations

from pathlib import Path

from tests.helpers.desktop_workspace_fakes import MappingPlanEntry, build_workspace_service


def test_batch_partial_failure_continues_after_one_file_fails(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"good.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
        failing_filenames={"bad.txt"},
    )
    good = tmp_path / "good.txt"
    bad = tmp_path / "bad.txt"
    good.write_text("Alice arrive", encoding="utf-8")
    bad.write_text("Bob arrive", encoding="utf-8")

    workspace = service.create_case("Dossier Partial")
    batch = service.run_case_anonymization(workspace.case_id, [good, bad])

    assert batch.status == "partial"
    assert batch.processed_count == 1
    assert batch.failed_count == 1
    assert batch.items[0].status == "success"
    assert batch.items[1].status == "failed"
    assert Path(batch.items[0].output_path).exists()
