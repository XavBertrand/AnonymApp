from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.config.desktop_settings import (
    APP_ROOT_ENV_VAR,
    DESKTOP_DATA_ROOT_ENV_VAR,
    DESKTOP_EXPORT_ROOT_ENV_VAR,
    WINDOWS_APP_DIRNAME,
    WINDOWS_DESKTOP_DATA_DIRNAME,
    WINDOWS_EXPORT_DIRNAME,
)

PORTABLE_DIST_DIRNAME = "a4_desktop_portable"
PORTABLE_EXECUTABLE_NAME = "A4Desktop.exe"
PORTABLE_LAUNCHER_NAME = "launch_a4_desktop.bat"
PORTABLE_SPEC_RELATIVE = Path("scripts/packaging/a4_desktop.spec")
ICON_CANDIDATES = (
    Path("src/app/desktop/assets/a4_desktop.ico"),
    Path("src/app/desktop/assets/a4_desktop.svg"),
)


@dataclass(frozen=True)
class PortableBuildPlan:
    project_root: Path
    dist_root: Path
    bundle_root: Path
    spec_path: Path
    launcher_path: Path
    executable_path: Path
    models_source: Path
    icon_source: Path | None


def build_portable_distribution(project_root: Path) -> Path:
    """Return the expected portable build directory for local packaging flows."""
    return portable_build_plan(project_root).bundle_root


def portable_build_plan(project_root: Path) -> PortableBuildPlan:
    root = project_root.resolve()
    bundle_root = root / "dist" / PORTABLE_DIST_DIRNAME
    return PortableBuildPlan(
        project_root=root,
        dist_root=root / "dist",
        bundle_root=bundle_root,
        spec_path=root / PORTABLE_SPEC_RELATIVE,
        launcher_path=bundle_root / PORTABLE_LAUNCHER_NAME,
        executable_path=bundle_root / PORTABLE_EXECUTABLE_NAME,
        models_source=root / "models",
        icon_source=portable_icon_resource(root),
    )


def portable_icon_resource(project_root: Path) -> Path | None:
    root = project_root.resolve()
    for relative in ICON_CANDIDATES:
        candidate = root / relative
        if candidate.exists():
            return candidate
    return None


def portable_datas(project_root: Path) -> tuple[tuple[str, str], ...]:
    plan = portable_build_plan(project_root)
    datas: list[tuple[str, str]] = []
    if plan.models_source.exists():
        datas.append((str(plan.models_source), "models"))
    if plan.icon_source is not None:
        datas.append((str(plan.icon_source.parent), "assets"))
    return tuple(datas)


def portable_runtime_env(
    *,
    portable_root_token: str = "%PORTABLE_ROOT%",
    local_appdata_token: str = "%LOCALAPPDATA%",
    user_profile_token: str = "%USERPROFILE%",
) -> dict[str, str]:
    normalized_root = portable_root_token.rstrip("\\/")
    return {
        APP_ROOT_ENV_VAR: normalized_root,
        DESKTOP_DATA_ROOT_ENV_VAR: (
            f"{local_appdata_token}\\{WINDOWS_APP_DIRNAME}\\{WINDOWS_DESKTOP_DATA_DIRNAME}"
        ),
        DESKTOP_EXPORT_ROOT_ENV_VAR: f"{user_profile_token}\\Documents\\{WINDOWS_EXPORT_DIRNAME}",
    }


def launcher_script_content(project_root: Path) -> str:
    plan = portable_build_plan(project_root)
    env = portable_runtime_env(portable_root_token="%PORTABLE_ROOT%")
    return "\n".join(
        (
            "@echo off",
            "setlocal",
            "set PORTABLE_ROOT=%~dp0",
            f"set {APP_ROOT_ENV_VAR}={env[APP_ROOT_ENV_VAR]}",
            f"set {DESKTOP_DATA_ROOT_ENV_VAR}={env[DESKTOP_DATA_ROOT_ENV_VAR]}",
            f"set {DESKTOP_EXPORT_ROOT_ENV_VAR}={env[DESKTOP_EXPORT_ROOT_ENV_VAR]}",
            f"if not exist \"%{APP_ROOT_ENV_VAR}%\\models\" echo Warning: models directory missing next to the executable.",
            f"start \"\" \"%{APP_ROOT_ENV_VAR}%\\{plan.executable_path.name}\"",
        )
    )


if __name__ == "__main__":  # pragma: no cover
    print(build_portable_distribution(Path(__file__).resolve().parents[2]))
