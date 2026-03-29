from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.packaging.build_windows_portable import WINDOWS_BUILD_ENTRYPOINT_RELATIVE
from scripts.packaging.verify_staged_release import (
    BUILD_INFO_RELATIVE,
    COMMIT_RELATIVE,
    DEFAULT_STAGE_RELATIVE,
    NEXT_STEPS_RELATIVE,
    verify_staged_release,
)

DEFAULT_TEST_COMMANDS = (
    (
        "desktop-regression",
        [
            "uv",
            "run",
            "pytest",
            "-q",
            "tests/ui/test_desktop_workspace_smoke.py",
            "tests/packaging/test_windows_portable_smoke.py",
            "tests/packaging/test_desktop_performance_smoke.py",
            "tests/integration/test_case_review_safety.py",
            "tests/integration/test_pasted_deanonymization_safety.py",
        ],
    ),
    (
        "packaging-safety",
        [
            "uv",
            "run",
            "pytest",
            "-q",
            "tests/packaging/test_portable_readiness_failures.py",
            "tests/unit/persistence/test_case_storage_integrity.py",
        ],
    ),
)
REQUIRED_STAGE_PATHS = (
    Path("pyproject.toml"),
    Path("README.md"),
    Path("src"),
    Path("models"),
    Path("scripts/packaging/a4_desktop.spec"),
    Path("scripts/packaging/build_windows.ps1"),
    Path("scripts/packaging/build_windows_portable.py"),
    Path("scripts/packaging/prepare_windows_test_release.py"),
    Path("scripts/packaging/smoke_test_portable.py"),
    Path("scripts/packaging/verify_staged_release.py"),
    Path("src/app/desktop/assets"),
)
OPTIONAL_STAGE_PATHS = (
    Path("uv.lock"),
    Path("tests/packaging"),
)


@dataclass(frozen=True)
class GitMetadata:
    branch: str
    commit: str
    dirty: bool


@dataclass(frozen=True)
class CommandRunResult:
    name: str
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


def collect_git_metadata(repo_root: Path) -> GitMetadata:
    branch = _run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    commit = _run_git(repo_root, "rev-parse", "HEAD")
    dirty = bool(_run_git(repo_root, "status", "--short"))
    return GitMetadata(branch=branch, commit=commit, dirty=dirty)


def _run_git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def preflight_checks(repo_root: Path) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_STAGE_PATHS:
        target = repo_root / relative
        if not target.exists():
            errors.append(f"Required path missing: {relative}")
    models_root = repo_root / "models"
    if models_root.exists() and not any(models_root.iterdir()):
        errors.append("Required path models/ exists but is empty.")
    return errors


def run_test_commands(
    repo_root: Path,
    commands: tuple[tuple[str, list[str]], ...] = DEFAULT_TEST_COMMANDS,
) -> list[CommandRunResult]:
    results: list[CommandRunResult] = []
    env = {"PYTHONPATH": str(repo_root), **os.environ}
    for name, command in commands:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            text=True,
            env=env,
        )
        result = CommandRunResult(
            name=name,
            command=tuple(command),
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        results.append(result)
        if completed.returncode != 0:
            raise RuntimeError(
                f"Targeted test command failed: {name}\n"
                f"Command: {' '.join(command)}\n"
                f"{completed.stdout}\n{completed.stderr}"
            )
    return results


def stage_release_tree(repo_root: Path, stage_root: Path) -> None:
    if stage_root.exists():
        shutil.rmtree(stage_root)
    stage_root.mkdir(parents=True, exist_ok=True)

    for relative in REQUIRED_STAGE_PATHS + OPTIONAL_STAGE_PATHS:
        source = repo_root / relative
        if not source.exists():
            continue
        destination = stage_root / relative
        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


def write_build_metadata(
    stage_root: Path,
    *,
    git: GitMetadata,
    test_results: list[CommandRunResult],
    staging_completed: bool,
) -> None:
    build_info = {
        "branch": git.branch,
        "commit": git.commit,
        "repo_dirty": git.dirty,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "expected_models_path": "models",
        "expected_windows_build_entrypoint": str(WINDOWS_BUILD_ENTRYPOINT_RELATIVE),
        "staging_completed": staging_completed,
        "test_commands": [
            {
                "name": result.name,
                "command": list(result.command),
                "returncode": result.returncode,
            }
            for result in test_results
        ],
        "test_summary": {
            "ran": len(test_results),
            "passed": sum(result.returncode == 0 for result in test_results),
            "failed": sum(result.returncode != 0 for result in test_results),
        },
    }
    (stage_root / BUILD_INFO_RELATIVE).write_text(
        json.dumps(build_info, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (stage_root / COMMIT_RELATIVE).write_text(
        f"{git.commit}\nbranch={git.branch}\ndirty={git.dirty}\n",
        encoding="utf-8",
    )
    (stage_root / NEXT_STEPS_RELATIVE).write_text(
        "\n".join(
            (
                "Windows final build/test steps",
                "1. Copy this staged folder to a Windows machine.",
                "2. Open PowerShell in the staged folder root.",
                "3. Run:",
                f"   powershell -ExecutionPolicy Bypass -File {WINDOWS_BUILD_ENTRYPOINT_RELATIVE}",
                "4. Launch the built portable app from dist/a4_desktop_portable.",
                "5. Run the real Windows smoke workflow there.",
            )
        )
        + "\n",
        encoding="utf-8",
    )


def prepare_windows_test_release(
    repo_root: Path,
    *,
    stage_root: Path,
    run_tests: bool = True,
) -> dict[str, object]:
    errors = preflight_checks(repo_root)
    if errors:
        raise RuntimeError("\n".join(errors))

    git = collect_git_metadata(repo_root)
    test_results = run_test_commands(repo_root) if run_tests else []
    stage_release_tree(repo_root, stage_root)
    write_build_metadata(stage_root, git=git, test_results=test_results, staging_completed=True)
    verification = verify_staged_release(stage_root)
    if not verification.ready:
        raise RuntimeError("\n".join(verification.errors))
    return {
        "git": asdict(git),
        "stage_root": str(stage_root.resolve()),
        "tests": [asdict(result) for result in test_results],
        "verification": asdict(verification),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a Windows-ready staged desktop release folder from WSL/Linux."
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_STAGE_RELATIVE),
        help="Where to stage the release folder.",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip targeted test execution and only stage/verify the folder.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON summary output.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = prepare_windows_test_release(
        REPO_ROOT,
        stage_root=Path(args.output_dir),
        run_tests=not args.skip_tests,
    )
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"staged release ready: {result['stage_root']}")
        print("next steps:")
        print(f"- copy {result['stage_root']} to Windows")
        print(f"- run powershell -ExecutionPolicy Bypass -File {WINDOWS_BUILD_ENTRYPOINT_RELATIVE}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
