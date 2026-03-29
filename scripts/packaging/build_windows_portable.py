from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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
WINDOWS_BUILD_ENTRYPOINT_RELATIVE = Path("scripts/packaging/build_windows.ps1")
ICON_CANDIDATES = (
    Path("src/app/desktop/assets/a4_desktop.ico"),
    Path("src/app/desktop/assets/a4_desktop.svg"),
)
BACKEND_SCRIPT_RELATIVES = (
    Path("tmp/anonymizer.py"),
    Path("tmp/transformer_anonymizer.py"),
)
PYINSTALLER_HIDDEN_IMPORTS = (
    "transformers",
    "torch",
    "rapidfuzz",
    "unidecode",
    "gliner",
    "requests",
)
CONDA_RUNTIME_DLL_NAMES = (
    "sqlite3.dll",
    "libcrypto-3-x64.dll",
    "libssl-3-x64.dll",
    "ffi-8.dll",
    "libexpat.dll",
    "liblzma.dll",
    "libbz2.dll",
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
    for relative in BACKEND_SCRIPT_RELATIVES:
        source = plan.project_root / relative
        if source.exists():
            datas.append((str(source), str(relative.parent)))
    return tuple(datas)


def portable_hiddenimports() -> tuple[str, ...]:
    return PYINSTALLER_HIDDEN_IMPORTS


def _is_windows_build_host() -> bool:
    return os.name == "nt"


def _unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    ordered: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        ordered.append(resolved)
    return ordered


def _conda_prefix_candidates() -> list[Path]:
    raw_candidates = [
        os.environ.get("CONDA_PREFIX", ""),
        sys.base_prefix,
        sys.prefix,
        str(Path(sys.executable).resolve().parent.parent),
    ]
    prefixes = [Path(candidate).expanduser() for candidate in raw_candidates if candidate]
    return _unique_paths(prefixes)


def _conda_runtime_search_roots() -> list[Path]:
    roots: list[Path] = []
    for prefix in _conda_prefix_candidates():
        roots.extend(
            [
                prefix / "Library" / "bin",
                prefix / "DLLs",
                prefix / "bin",
                prefix,
            ]
        )
    return _unique_paths([root for root in roots if root.exists()])


def _find_runtime_dll(name: str, roots: list[Path]) -> Path | None:
    lowered = name.lower()
    for root in roots:
        direct = root / name
        if direct.exists():
            return direct
        for candidate in root.iterdir():
            if candidate.is_file() and candidate.name.lower() == lowered:
                return candidate
    return None


def portable_runtime_binaries(project_root: Path) -> tuple[tuple[str, str], ...]:
    _ = project_root
    if not _is_windows_build_host():
        return ()

    roots = _conda_runtime_search_roots()
    binaries: list[tuple[str, str]] = []
    for dll_name in CONDA_RUNTIME_DLL_NAMES:
        runtime_dll = _find_runtime_dll(dll_name, roots)
        if runtime_dll is not None:
            binaries.append((str(runtime_dll), "."))
    return tuple(binaries)


def portable_runtime_binaries_report(project_root: Path) -> tuple[str, ...]:
    _ = project_root
    if not _is_windows_build_host():
        return ("Conda runtime DLL detection is skipped outside Windows.",)

    roots = _conda_runtime_search_roots()
    report: list[str] = []
    for dll_name in CONDA_RUNTIME_DLL_NAMES:
        runtime_dll = _find_runtime_dll(dll_name, roots)
        if runtime_dll is not None:
            report.append(f"{dll_name} <= {runtime_dll}")
        else:
            report.append(f"{dll_name} <= missing")
    return tuple(report)


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
    print(build_portable_distribution(REPO_ROOT))
