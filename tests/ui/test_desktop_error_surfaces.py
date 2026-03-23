from __future__ import annotations

from pathlib import Path

import pytest

from src.app.desktop.presenters.workspace_presenter import WorkspacePresenter
from src.app.desktop.qt_compat import process_events
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
                        remediation="Installer les modeles",
                    )
                ],
            )
        ]

    return ReadinessService(bootstrap_provider=_provider)


def test_window_surfaces_global_error_banner_for_blocked_actions(tmp_path: Path) -> None:
    service = build_workspace_service(tmp_path, readiness_service=_blocked_readiness_service())
    window = DesktopMainWindow(WorkspacePresenter(service))
    window.load()
    window.create_case("Dossier Bloque")
    input_path = tmp_path / "piece.txt"
    input_path.write_text("Alice", encoding="utf-8")

    window.run_case_anonymization([input_path])
    with pytest.raises(ValueError):
        window.pending_batch.result(timeout=2)
    process_events()

    assert window.error_banner.message is not None
    assert "indisponible" in window.error_banner.message.lower()


def test_case_workspace_panel_tracks_per_file_errors_from_partial_batch(tmp_path: Path) -> None:
    service = build_workspace_service(tmp_path, failing_filenames={"bad.txt"})
    window = DesktopMainWindow(WorkspacePresenter(service))
    window.load()
    window.create_case("Dossier Batch Error")
    good = tmp_path / "good.txt"
    bad = tmp_path / "bad.txt"
    good.write_text("Alice", encoding="utf-8")
    bad.write_text("Bob", encoding="utf-8")

    window.run_case_anonymization([good, bad])
    window.pending_batch.result(timeout=2)
    process_events()

    assert window.case_workspace_panel.last_batch is not None
    assert window.case_workspace_panel.file_errors
    assert window.case_workspace_panel.file_errors[0].startswith("Echec")
