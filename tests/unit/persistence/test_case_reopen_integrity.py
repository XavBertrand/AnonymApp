from __future__ import annotations

from pathlib import Path

from src.adapters.persistence.artifact_repository import ArtifactRepository
from src.adapters.persistence.case_repository import CaseRepository
from src.adapters.persistence.database import MetadataDatabase
from tests.helpers.desktop_workspace_fakes import MappingPlanEntry, build_workspace_service


def test_case_history_order_updates_when_case_is_reopened(tmp_path: Path) -> None:
    database = MetadataDatabase(tmp_path / "desktop.sqlite3")
    database.bootstrap()
    repository = CaseRepository(database)
    first = repository.create("Premier Dossier")
    second = repository.create("Second Dossier")

    repository.set_last_opened(first.case_id)

    ordered = repository.list_active()

    assert ordered[0].case_id == first.case_id
    assert ordered[1].case_id == second.case_id


def test_missing_artifact_lookup_preserves_reopen_metadata(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"doc.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    input_path = tmp_path / "doc.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    workspace = service.create_case("Dossier Missing")
    batch = service.run_case_anonymization(workspace.case_id, [input_path])
    output_path = Path(batch.items[0].output_path)
    output_path.unlink()

    artifact_repository = ArtifactRepository(service._database)
    missing_ids = artifact_repository.list_missing_ids(workspace.case_id)
    reopened = service.open_case(workspace.case_id)

    assert reopened.documents[0].document_id is not None
    assert reopened.documents[0].latest_output_path == str(output_path)
    assert reopened.documents[0].latest_output_status == "missing"
    assert reopened.artifacts[0].artifact_id in missing_ids
    assert reopened.artifacts[0].status == "missing"
