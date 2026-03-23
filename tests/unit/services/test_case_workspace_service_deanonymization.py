from __future__ import annotations

from pathlib import Path

from tests.helpers.desktop_workspace_fakes import MappingPlanEntry, build_workspace_service


def test_pasted_deanonymization_uses_active_mapping_revision_and_persists_session(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"piece.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    input_path = tmp_path / "piece.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    workspace = service.create_case("Dossier Deanon")
    service.run_case_anonymization(workspace.case_id, [input_path])

    session = service.deanonymize_pasted_text(workspace.case_id, "<PERSON_1> arrive")

    assert session.result_text == "Alice arrive"
    assert session.result_state == "matched"
    assert session.match_count == 1
    assert session.mapping_revision == 1
    persisted = service._deanonymization_session_repository.get(session.session_id)
    assert persisted is not None
    assert Path(persisted.result_text_path).read_text(encoding="utf-8") == "Alice arrive"


def test_pasted_deanonymization_export_persists_artifact_and_links_session(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"piece.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    input_path = tmp_path / "piece.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    workspace = service.create_case("Dossier Export")
    service.run_case_anonymization(workspace.case_id, [input_path])
    session = service.deanonymize_pasted_text(workspace.case_id, "<PERSON_1> arrive")

    export = service.export_deanonymized_result(workspace.case_id, session.session_id)

    assert Path(export.file_path).read_text(encoding="utf-8") == "Alice arrive"
    assert export.session.exported_artifact_id == export.artifact_id
    persisted = service._deanonymization_session_repository.get(session.session_id)
    assert persisted is not None
    assert persisted.exported_artifact_id == export.artifact_id


def test_pasted_deanonymization_zero_match_keeps_text_unchanged(tmp_path: Path) -> None:
    service = build_workspace_service(tmp_path)
    workspace = service.create_case("Dossier Zero")

    session = service.deanonymize_pasted_text(workspace.case_id, "<PERSON_9> arrive")

    assert session.result_text == "<PERSON_9> arrive"
    assert session.result_state == "no_match"
    assert session.match_count == 0
    assert session.mapping_revision is None
