from __future__ import annotations

from pathlib import Path

from tests.helpers.desktop_workspace_fakes import MappingPlanEntry, build_workspace_service


def test_shared_mapping_is_reused_across_multiple_txt_files(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={
            "first.txt": [MappingPlanEntry("Alice", "<PERSON_1>")],
            "second.txt": [MappingPlanEntry("Alice", "<PERSON_2>")],
        },
    )
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("Alice arrive", encoding="utf-8")
    second.write_text("Alice repart", encoding="utf-8")

    workspace = service.create_case("Dossier Shared")
    batch = service.run_case_anonymization(workspace.case_id, [first, second])

    assert batch.status == "success"
    first_output = Path(batch.items[0].output_path).read_text(encoding="utf-8")
    second_output = Path(batch.items[1].output_path).read_text(encoding="utf-8")
    assert first_output == "<PERSON_1> arrive"
    assert second_output == "<PERSON_1> repart"
    assert batch.workspace.active_mapping_revision == 1
