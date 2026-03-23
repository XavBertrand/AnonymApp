from __future__ import annotations

from pathlib import Path
from threading import Event, Thread
from types import SimpleNamespace

import pytest

from src.adapters.persistence.artifact_repository import ArtifactRepository
from src.services.case_workspace_service import CaseDeletionBlockedError
from tests.helpers.desktop_workspace_fakes import MappingPlanEntry, build_workspace_service


class BlockingDeanonymizationService:
    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()

    def run_text(self, *, input_text: str, mapping_artifact):
        self.started.set()
        self.release.wait(timeout=5)
        restored = input_text
        for entry in sorted(mapping_artifact.entries, key=lambda item: len(item.placeholder), reverse=True):
            restored = restored.replace(entry.placeholder, entry.original_value)
        return SimpleNamespace(
            deanonymized_text=restored,
            engine_id=mapping_artifact.origin.engine_id,
        )


class FailingArtifactRepository(ArtifactRepository):
    def create(self, record, *, connection=None):
        raise RuntimeError("artifact write failed")


def test_delete_case_is_refused_while_pasted_deanonymization_job_is_running(tmp_path: Path) -> None:
    blocker = BlockingDeanonymizationService()
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"piece.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
        deanonymization_service=blocker,
    )
    input_path = tmp_path / "piece.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    workspace = service.create_case("Dossier Delete Guard")
    service.run_case_anonymization(workspace.case_id, [input_path])

    result_holder: dict[str, object] = {}

    def _run() -> None:
        result_holder["session"] = service.deanonymize_pasted_text(workspace.case_id, "<PERSON_1> arrive")

    worker = Thread(target=_run)
    worker.start()
    assert blocker.started.wait(timeout=2)

    with pytest.raises(CaseDeletionBlockedError):
        service.delete_case(workspace.case_id, confirmed=True)

    blocker.release.set()
    worker.join(timeout=2)
    assert "session" in result_holder
    persisted = service._deanonymization_session_repository.get(result_holder["session"].session_id)
    assert persisted is not None


def test_reexport_marks_previous_export_superseded_and_updates_session_link(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"piece.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    input_path = tmp_path / "piece.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    workspace = service.create_case("Dossier Reexport")
    service.run_case_anonymization(workspace.case_id, [input_path])
    session = service.deanonymize_pasted_text(workspace.case_id, "<PERSON_1> arrive")

    first_export = service.export_deanonymized_result(workspace.case_id, session.session_id)
    second_export = service.export_deanonymized_result(workspace.case_id, session.session_id)

    first_record = service._artifact_repository.get(first_export.artifact_id)
    second_record = service._artifact_repository.get(second_export.artifact_id)
    persisted_session = service._deanonymization_session_repository.get(session.session_id)

    assert first_record is not None and first_record.artifact_status == "superseded"
    assert second_record is not None and second_record.artifact_status == "current"
    assert persisted_session is not None and persisted_session.exported_artifact_id == second_export.artifact_id
    assert first_export.file_path != second_export.file_path


def test_export_refuses_existing_user_destination_without_overwriting_it(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"piece.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    input_path = tmp_path / "piece.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    workspace = service.create_case("Dossier Existing Export")
    service.run_case_anonymization(workspace.case_id, [input_path])
    session = service.deanonymize_pasted_text(workspace.case_id, "<PERSON_1> arrive")
    destination = tmp_path / "existing.txt"
    destination.write_text("do-not-touch", encoding="utf-8")

    with pytest.raises(ValueError, match="existe deja"):
        service.export_deanonymized_result(workspace.case_id, session.session_id, destination)

    assert destination.read_text(encoding="utf-8") == "do-not-touch"


def test_export_failure_cleans_new_file_and_keeps_session_link_consistent(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"piece.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    input_path = tmp_path / "piece.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    workspace = service.create_case("Dossier Export Failure")
    service.run_case_anonymization(workspace.case_id, [input_path])
    session = service.deanonymize_pasted_text(workspace.case_id, "<PERSON_1> arrive")
    existing_session = service._deanonymization_session_repository.get(session.session_id)

    failing = build_workspace_service(
        tmp_path,
        artifact_repository=FailingArtifactRepository(service._database),
    )
    destination = tmp_path / "new-export.txt"

    with pytest.raises(RuntimeError, match="artifact write failed"):
        failing.export_deanonymized_result(workspace.case_id, session.session_id, destination)

    assert not destination.exists()
    persisted_session = service._deanonymization_session_repository.get(session.session_id)
    assert persisted_session == existing_session
