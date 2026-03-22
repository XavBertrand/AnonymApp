from __future__ import annotations

from src.adapters.persistence.records import JobRecord
from src.services.case_workspace_service import CaseDeletionBlockedError, CaseWorkspaceService
import pytest

from tests.helpers.desktop_workspace_fakes import build_workspace_service


def test_delete_case_requires_confirmation_and_hides_deleted_case_from_history(tmp_path) -> None:
    service = build_workspace_service(tmp_path)
    first = service.create_case("Dossier A")
    second = service.create_case("Dossier B")

    with pytest.raises(ValueError):
        service.delete_case(first.case_id, confirmed=False)

    after_delete = service.delete_case(first.case_id, confirmed=True)

    remaining_ids = {item.case_id for item in after_delete.cases}
    assert first.case_id not in remaining_ids
    assert second.case_id in remaining_ids
    with pytest.raises(ValueError):
        service.open_case(first.case_id)


def test_delete_case_is_refused_while_a_batch_job_is_running(tmp_path) -> None:
    service = build_workspace_service(tmp_path)
    workspace = service.create_case("Dossier Running")
    running_job = JobRecord(
        job_id="job-running",
        case_id=workspace.case_id,
        job_type="anonymization_batch",
        started_at="2026-03-22T10:00:00+00:00",
        completed_at=None,
        job_status="running",
        mapping_revision_used=None,
        item_count=1,
        success_count=0,
        failure_count=0,
        error_summary=None,
        readiness_snapshot="[]",
    )
    service._job_repository.create(running_job)

    with pytest.raises(CaseDeletionBlockedError) as exc:
        service.delete_case(workspace.case_id, confirmed=True)

    assert str(exc.value) == CaseWorkspaceService.DELETE_WHILE_RUNNING_MESSAGE
    assert service._case_repository.get(workspace.case_id) is not None
    assert service._document_repository.list_by_case(workspace.case_id) == []
    assert service._artifact_repository.list_by_case(workspace.case_id) == []
    assert len(service._job_repository.list_by_case(workspace.case_id)) == 1
