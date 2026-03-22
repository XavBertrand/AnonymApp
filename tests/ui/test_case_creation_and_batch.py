from __future__ import annotations

from pathlib import Path

from src.app.desktop.qt_compat import process_events
from src.app.desktop.presenters.workspace_presenter import WorkspacePresenter
from src.app.desktop.window import DesktopMainWindow
from tests.helpers.desktop_workspace_fakes import MappingPlanEntry, build_workspace_service


class ControlledWorker:
    def __init__(self) -> None:
        self._completion = None

    def submit(self, fn, /, *args, on_success=None, on_error=None, **kwargs):
        def _complete_success() -> None:
            try:
                result = fn(*args, **kwargs)
            except Exception as exc:  # pragma: no cover - not used in this test
                if on_error is not None:
                    on_error(exc)
            else:
                if on_success is not None:
                    on_success(result)

        self._completion = _complete_success
        return "pending-future"

    def complete(self) -> None:
        assert self._completion is not None
        self._completion()


def test_desktop_window_create_case_and_run_batch(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"doc.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    presenter = WorkspacePresenter(service)
    window = DesktopMainWindow(presenter)
    window.load()

    input_path = tmp_path / "doc.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    window.create_case("Dossier UI")
    window.run_case_anonymization([input_path])
    assert window.pending_batch is not None
    window.pending_batch.result(timeout=2)
    process_events()

    assert window.current_case_id is not None
    assert window.case_workspace_panel.last_batch is not None
    assert Path(window.case_workspace_panel.last_batch.items[0].output_path).exists()


def test_desktop_window_batch_execution_is_non_blocking_until_worker_completes(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"doc.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    presenter = WorkspacePresenter(service)
    worker = ControlledWorker()
    window = DesktopMainWindow(presenter, worker=worker)
    window.load()

    input_path = tmp_path / "doc.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    window.create_case("Dossier Async")
    window.run_case_anonymization([input_path])

    assert window.pending_batch == "pending-future"
    assert window.case_workspace_panel.last_batch is None

    worker.complete()
    process_events()

    assert window.pending_batch is None
    assert window.case_workspace_panel.last_batch is not None
