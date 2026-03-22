from __future__ import annotations

from src.app.desktop.presenters.workspace_presenter import WorkspacePresenter
from src.app.desktop.widgets.delete_case_dialog import DeleteCaseDialog
from src.app.desktop.window import DesktopMainWindow
from src.adapters.persistence.records import JobRecord
from src.services.case_workspace_service import CaseWorkspaceService
from tests.helpers.desktop_workspace_fakes import build_workspace_service


def test_delete_case_flow_respects_confirmation_and_refreshes_history(tmp_path) -> None:
    service = build_workspace_service(tmp_path)
    first = service.create_case("Dossier Un")
    second = service.create_case("Dossier Deux")
    dialog = DeleteCaseDialog()
    presenter = WorkspacePresenter(service)
    window = DesktopMainWindow(presenter, delete_case_dialog=dialog)
    window.load()

    dialog.set_next_response(False)
    window.case_history_panel.request_delete_case(second.case_id)

    assert {item.case_id for item in window.case_history_panel.items} == {first.case_id, second.case_id}

    dialog.set_next_response(True)
    window.case_history_panel.request_delete_case(second.case_id)

    remaining_ids = {item.case_id for item in window.case_history_panel.items}
    assert second.case_id not in remaining_ids
    assert first.case_id in remaining_ids
    assert window.current_case_id == first.case_id
    assert dialog.last_requested_display_name == "Dossier Deux"


def test_delete_case_flow_is_blocked_when_selected_case_is_processing(tmp_path) -> None:
    service = build_workspace_service(tmp_path)
    workspace = service.create_case("Dossier Running")
    service._job_repository.create(
        JobRecord(
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
    )
    dialog = DeleteCaseDialog()
    presenter = WorkspacePresenter(service)
    window = DesktopMainWindow(presenter, delete_case_dialog=dialog)
    window.load()

    running_case = next(item for item in window.case_history_panel.items if item.case_id == workspace.case_id)

    assert running_case.delete_available is False
    assert running_case.delete_unavailable_reason == CaseWorkspaceService.DELETE_WHILE_RUNNING_MESSAGE

    window.case_history_panel.request_delete_case(workspace.case_id)

    assert dialog.last_requested_display_name is None
    assert dialog.last_blocked_message is None
    assert window.case_history_panel.last_delete_block_reason == CaseWorkspaceService.DELETE_WHILE_RUNNING_MESSAGE


def test_delete_case_flow_is_blocked_immediately_when_local_batch_is_pending(tmp_path) -> None:
    service = build_workspace_service(tmp_path)
    workspace = service.create_case("Dossier Pending")
    dialog = DeleteCaseDialog()
    presenter = WorkspacePresenter(service)
    window = DesktopMainWindow(presenter, delete_case_dialog=dialog)
    window.load()
    window.current_case_id = workspace.case_id
    window.pending_batch = "pending-future"

    window.delete_case(workspace.case_id)

    assert window.last_error == CaseWorkspaceService.DELETE_WHILE_RUNNING_MESSAGE
    assert dialog.last_blocked_message == CaseWorkspaceService.DELETE_WHILE_RUNNING_MESSAGE
