from __future__ import annotations

import json
from pathlib import Path

from tests.helpers.desktop_workspace_fakes import MappingPlanEntry, build_workspace_service


def test_missing_artifact_reconciliation_marks_record_missing_and_cleans_temp_files(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"piece.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    input_path = tmp_path / "piece.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    workspace = service.create_case("Dossier Integrity")
    batch = service.run_case_anonymization(workspace.case_id, [input_path])
    artifact_path = Path(batch.items[0].output_path)
    artifact_path.unlink()

    case_root = service._artifact_store.case_root(workspace.case_id, "Dossier Integrity")
    temp_file = case_root / "sessions" / ".orphan.tmp"
    temp_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file.write_text("temp", encoding="utf-8")

    reopened = service.open_case(workspace.case_id)
    record = service._artifact_repository.get(reopened.artifacts[0].artifact_id)

    assert record is not None
    assert record.artifact_status == "missing"
    assert reopened.artifacts[0].status == "missing"
    assert not temp_file.exists()


def test_job_readiness_snapshots_are_persisted_for_case_inspection(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"piece.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    input_path = tmp_path / "piece.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    workspace = service.create_case("Dossier Snapshots")
    service.run_case_anonymization(workspace.case_id, [input_path])
    service.deanonymize_pasted_text(workspace.case_id, "<PERSON_1> arrive")

    snapshots = service._job_repository.list_readiness_snapshots(workspace.case_id)

    assert len(snapshots) == 2
    assert all(json.loads(snapshot)[0]["engine_id"] == "transformer" for snapshot in snapshots)
