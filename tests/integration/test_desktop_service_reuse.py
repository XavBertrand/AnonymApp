from __future__ import annotations

import subprocess
from pathlib import Path

from tests.helpers.desktop_workspace_fakes import MappingPlanEntry, build_workspace_service


def test_desktop_workspace_reuses_service_layer_without_cli_shell_out(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []

    def _fail(*args, **kwargs):
        calls.append(str(args[0]) if args else "unknown")
        raise AssertionError("Desktop workflow must not shell out to the CLI")

    monkeypatch.setattr(subprocess, "run", _fail)
    monkeypatch.setattr(subprocess, "Popen", _fail)

    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"doc.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    path = tmp_path / "doc.txt"
    path.write_text("Alice arrive", encoding="utf-8")
    workspace = service.create_case("Dossier Direct")

    batch = service.run_case_anonymization(workspace.case_id, [path])

    assert batch.status == "success"
    assert calls == []
