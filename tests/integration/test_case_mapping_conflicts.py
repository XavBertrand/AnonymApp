from __future__ import annotations

from pathlib import Path

from tests.helpers.desktop_workspace_fakes import MappingPlanEntry, build_workspace_service


def test_conflicting_pseudonyms_resolve_with_earliest_mapping(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={
            "a.txt": [MappingPlanEntry("Alice", "<PERSON_1>")],
            "b.txt": [MappingPlanEntry("Alice", "<PERSON_9>")],
        },
    )
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_text("Alice voit Bob", encoding="utf-8")
    second.write_text("Alice parle", encoding="utf-8")

    workspace = service.create_case("Dossier Conflit")
    batch = service.run_case_anonymization(workspace.case_id, [first, second])

    assert batch.items[0].mapping_revision == 1
    assert batch.items[1].mapping_revision == 1
    assert Path(batch.items[1].output_path).read_text(encoding="utf-8") == "<PERSON_1> parle"
