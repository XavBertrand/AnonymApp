from __future__ import annotations

from pathlib import Path
from time import perf_counter

from src.app.desktop.presenters.workspace_presenter import WorkspacePresenter
from src.app.desktop.window import DesktopMainWindow
from tests.helpers.desktop_workspace_fakes import MappingPlanEntry, build_workspace_service


class ControlledWorker:
    def __init__(self) -> None:
        self._completion = None

    def submit(self, fn, /, *args, on_success=None, on_error=None, **kwargs):
        def _complete() -> None:
            try:
                result = fn(*args, **kwargs)
            except Exception as exc:  # pragma: no cover - not used in this smoke test
                if on_error is not None:
                    on_error(exc)
            else:
                if on_success is not None:
                    on_success(result)

        self._completion = _complete
        return "pending-future"


def test_desktop_startup_load_is_usable_within_target(tmp_path: Path) -> None:
    start = perf_counter()
    window = DesktopMainWindow(WorkspacePresenter(build_workspace_service(tmp_path)))
    window.load()
    elapsed = perf_counter() - start

    assert elapsed < 5.0
    assert window.readiness_panel.summary is not None


def test_case_switch_feels_immediate_in_fake_workspace(tmp_path: Path) -> None:
    service = build_workspace_service(tmp_path)
    window = DesktopMainWindow(WorkspacePresenter(service))
    window.load()
    first = service.create_case("Dossier A")
    second = service.create_case("Dossier B")

    start = perf_counter()
    window.open_case(first.case_id)
    window.open_case(second.case_id)
    elapsed = perf_counter() - start

    assert elapsed < 1.0
    assert window.current_case_id == second.case_id


def test_first_progress_signal_is_visible_immediately_when_batch_starts(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"piece.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    worker = ControlledWorker()
    window = DesktopMainWindow(WorkspacePresenter(service), worker=worker)
    window.load()
    window.create_case("Dossier Perf")
    input_path = tmp_path / "piece.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    start = perf_counter()
    window.run_case_anonymization([input_path])
    elapsed = perf_counter() - start

    assert elapsed < 1.0
    assert window.pending_batch == "pending-future"
    assert window.case_workspace_panel.status_message == "Traitement en cours..."
