from __future__ import annotations

from pathlib import Path

from tests.helpers.desktop_workspace_fakes import MappingPlanEntry, build_workspace_service


def test_case_round_trip_coherence_for_batch_output_and_pasted_deanonymization(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"piece.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    input_path = tmp_path / "piece.txt"
    input_path.write_text("Alice arrive chez Alice", encoding="utf-8")

    workspace = service.create_case("Dossier Round Trip")
    batch = service.run_case_anonymization(workspace.case_id, [input_path])
    anonymized_text = Path(batch.items[0].output_path).read_text(encoding="utf-8")

    session = service.deanonymize_pasted_text(workspace.case_id, anonymized_text)

    assert session.result_state == "matched"
    assert session.match_count == 2
    assert session.result_text == "Alice arrive chez Alice"
