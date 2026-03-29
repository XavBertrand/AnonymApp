from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.packaging.build_windows_portable import (
    PORTABLE_SPEC_RELATIVE,
    WINDOWS_BUILD_ENTRYPOINT_RELATIVE,
)
from scripts.packaging.smoke_test_portable import portable_smoke_report

DEFAULT_STAGE_RELATIVE = Path("out/windows_test_release")
BUILD_INFO_RELATIVE = Path("build_info.json")
NEXT_STEPS_RELATIVE = Path("next_steps_windows.txt")
COMMIT_RELATIVE = Path("commit.txt")
REQUIRED_STAGE_FILES = (
    Path("pyproject.toml"),
    PORTABLE_SPEC_RELATIVE,
    WINDOWS_BUILD_ENTRYPOINT_RELATIVE,
    Path("scripts/packaging/build_windows_portable.py"),
    Path("scripts/packaging/smoke_test_portable.py"),
    Path("scripts/packaging/prepare_windows_test_release.py"),
    Path("scripts/packaging/verify_staged_release.py"),
    Path("src/app/desktop/assets/a4_desktop.svg"),
    BUILD_INFO_RELATIVE,
    NEXT_STEPS_RELATIVE,
    COMMIT_RELATIVE,
)
REQUIRED_STAGE_DIRECTORIES = (
    Path("models"),
    Path("src"),
    Path("scripts/packaging"),
)


@dataclass(frozen=True)
class StageVerificationResult:
    ready: bool
    stage_root: str
    errors: tuple[str, ...]
    checks: dict[str, str]


def verify_staged_release(stage_root: Path) -> StageVerificationResult:
    root = stage_root.resolve()
    errors: list[str] = []
    checks: dict[str, str] = {}

    if not root.exists():
        return StageVerificationResult(
            ready=False,
            stage_root=str(root),
            errors=(f"Staged release folder not found: {root}",),
            checks={},
        )

    for relative in REQUIRED_STAGE_FILES:
        target = root / relative
        if target.exists():
            checks[str(relative)] = "present"
        else:
            message = f"Missing required file: {relative}"
            checks[str(relative)] = message
            errors.append(message)

    for relative in REQUIRED_STAGE_DIRECTORIES:
        target = root / relative
        if target.is_dir():
            checks[f"{relative}/"] = "present"
        else:
            message = f"Missing required directory: {relative}"
            checks[f"{relative}/"] = message
            errors.append(message)

    models_root = root / "models"
    if models_root.is_dir() and any(models_root.iterdir()):
        checks["models_populated"] = "ready"
    else:
        message = "Models directory is missing or empty."
        checks["models_populated"] = message
        errors.append(message)

    build_info_path = root / BUILD_INFO_RELATIVE
    if build_info_path.exists():
        try:
            build_info = json.loads(build_info_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            message = f"build_info.json is invalid JSON: {exc}"
            checks["build_info"] = message
            errors.append(message)
        else:
            if build_info.get("staging_completed") is True:
                checks["build_info"] = "ready"
            else:
                message = "build_info.json does not mark staging as completed."
                checks["build_info"] = message
                errors.append(message)
    else:
        checks["build_info"] = "missing"

    portable_report = portable_smoke_report(root)
    for name, (state, detail) in portable_report.items():
        checks[f"portable:{name}"] = f"{state}: {detail}"
        if state != "ready":
            errors.append(f"Portable smoke check failed for {name}: {detail}")

    return StageVerificationResult(
        ready=not errors,
        stage_root=str(root),
        errors=tuple(errors),
        checks=checks,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify that a staged desktop release folder is ready to copy to Windows."
    )
    parser.add_argument(
        "stage_root",
        nargs="?",
        default=str(DEFAULT_STAGE_RELATIVE),
        help="Path to the staged release folder.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a JSON report instead of plain text.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = verify_staged_release(Path(args.stage_root))
    if args.json:
        print(json.dumps(asdict(result), indent=2, sort_keys=True))
    elif result.ready:
        print(f"ready to copy to Windows: {result.stage_root}")
    else:
        print(f"blocked: {result.stage_root}")
        for error in result.errors:
            print(f"- {error}")
    return 0 if result.ready else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
