from __future__ import annotations

import json
from pathlib import Path

from scripts.packaging.prepare_windows_test_release import (
    CommandRunResult,
    COMMIT_RELATIVE,
    GitMetadata,
    NEXT_STEPS_RELATIVE,
    prepare_windows_test_release,
)
from scripts.packaging.verify_staged_release import BUILD_INFO_RELATIVE, verify_staged_release


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_minimal_repo(repo_root: Path) -> None:
    _write(repo_root / "pyproject.toml", "[project]\nname='anonymapp'\n")
    _write(repo_root / "README.md", "# AnonymApp\n")
    _write(repo_root / "src" / "app" / "desktop" / "assets" / "a4_desktop.svg", "<svg/>\n")
    _write(repo_root / "src" / "placeholder.py", "VALUE = 1\n")
    _write(repo_root / "models" / "model.bin", "ok\n")
    _write(repo_root / "scripts" / "packaging" / "a4_desktop.spec", "# spec\n")
    _write(repo_root / "scripts" / "packaging" / "build_windows.ps1", "Write-Host 'ok'\n")
    _write(repo_root / "scripts" / "packaging" / "build_windows_portable.py", "# helper\n")
    _write(repo_root / "scripts" / "packaging" / "prepare_windows_test_release.py", "# prep\n")
    _write(repo_root / "scripts" / "packaging" / "smoke_test_portable.py", "# smoke\n")
    _write(repo_root / "scripts" / "packaging" / "verify_staged_release.py", "# verify\n")


def test_prepare_windows_test_release_writes_manifest_and_ready_stage(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root = tmp_path / "repo"
    stage_root = tmp_path / "stage"
    _build_minimal_repo(repo_root)

    monkeypatch.setattr(
        "scripts.packaging.prepare_windows_test_release.collect_git_metadata",
        lambda _repo_root: GitMetadata(branch="002-desktop-case-ui", commit="abc123", dirty=False),
    )
    monkeypatch.setattr(
        "scripts.packaging.prepare_windows_test_release.run_test_commands",
        lambda _repo_root: [
            CommandRunResult(
                name="desktop-regression",
                command=("uv", "run", "pytest", "-q", "tests/ui/test_desktop_workspace_smoke.py"),
                returncode=0,
                stdout="3 passed\n",
                stderr="",
            )
        ],
    )

    result = prepare_windows_test_release(repo_root, stage_root=stage_root, run_tests=True)

    build_info = json.loads((stage_root / BUILD_INFO_RELATIVE).read_text(encoding="utf-8"))
    assert result["verification"]["ready"] is True
    assert build_info["branch"] == "002-desktop-case-ui"
    assert build_info["commit"] == "abc123"
    assert build_info["test_summary"]["passed"] == 1
    assert build_info["staging_completed"] is True
    assert (stage_root / COMMIT_RELATIVE).read_text(encoding="utf-8").startswith("abc123")
    assert "build_windows.ps1" in (stage_root / NEXT_STEPS_RELATIVE).read_text(encoding="utf-8")
    assert verify_staged_release(stage_root).ready is True


def test_verify_staged_release_reports_missing_models(tmp_path: Path) -> None:
    stage_root = tmp_path / "stage"
    _build_minimal_repo(stage_root)
    (stage_root / BUILD_INFO_RELATIVE).write_text(
        json.dumps({"staging_completed": True}),
        encoding="utf-8",
    )
    (stage_root / COMMIT_RELATIVE).write_text("abc123\n", encoding="utf-8")
    (stage_root / NEXT_STEPS_RELATIVE).write_text("next\n", encoding="utf-8")
    models_root = stage_root / "models"
    for child in models_root.iterdir():
        child.unlink()

    result = verify_staged_release(stage_root)

    assert result.ready is False
    assert "Models directory is missing or empty." in result.errors


def test_prepare_windows_test_release_fails_fast_when_required_models_are_missing(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    _build_minimal_repo(repo_root)
    for child in (repo_root / "models").iterdir():
        child.unlink()

    try:
        prepare_windows_test_release(repo_root, stage_root=tmp_path / "stage", run_tests=False)
    except RuntimeError as exc:
        assert "models/" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected preflight failure when models are missing")
