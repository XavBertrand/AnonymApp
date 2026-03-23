from __future__ import annotations

from src.app.desktop.presenters.workspace_presenter import WorkspacePresenter
from src.app.desktop.widgets.readiness_details_dialog import ReadinessDetailsDialog
from src.app.desktop.window import DesktopMainWindow
from src.models.backend_descriptor import BackendDescriptor, ReadinessCheckResult
from src.services.readiness_service import ReadinessService
from tests.helpers.desktop_workspace_fakes import build_workspace_service


def _blocked_readiness_service() -> ReadinessService:
    def _provider() -> list[BackendDescriptor]:
        return [
            BackendDescriptor(
                engine_id="transformer",
                display_name="Transformer",
                availability_status="unavailable",
                readiness_checks=[
                    ReadinessCheckResult(
                        check_name="models",
                        severity="critical",
                        status="fail",
                        message="missing",
                        remediation="Install models",
                    )
                ],
            )
        ]

    return ReadinessService(bootstrap_provider=_provider)


def test_readiness_panel_shows_summary_and_details(tmp_path) -> None:
    service = build_workspace_service(tmp_path, readiness_service=_blocked_readiness_service())
    presenter = WorkspacePresenter(service)
    dialog = ReadinessDetailsDialog()
    window = DesktopMainWindow(presenter, readiness_details_dialog=dialog)

    window.load()
    window.readiness_panel.request_show_details()

    assert window.readiness_panel.summary is not None
    assert window.readiness_panel.summary.state == "blocked"
    assert dialog.last_model is not None
    assert dialog.last_model.backends[0].availability_status == "unavailable"
    assert dialog.last_model.backends[0].checks[0].remediation == "Install models"
