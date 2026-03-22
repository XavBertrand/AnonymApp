from __future__ import annotations

from pathlib import Path

from tests.helpers.desktop_workspace_fakes import MappingPlanEntry, build_workspace_service


def test_case_workspace_service_creates_opens_and_batches_documents(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"doc.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    input_path = tmp_path / "doc.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    workspace = service.create_case("Dossier Batch")
    reopened = service.open_case(workspace.case_id)
    batch = service.run_case_anonymization(workspace.case_id, [input_path])

    assert reopened.case_id == workspace.case_id
    assert batch.status == "success"
    assert batch.processed_count == 1
    assert batch.failed_count == 0
    assert batch.workspace.documents[0].status == "success"
    assert Path(batch.items[0].output_path).exists()
