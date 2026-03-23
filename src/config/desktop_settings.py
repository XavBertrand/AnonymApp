from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from src.config.settings import PROJECT_ROOT

APP_ROOT_ENV_VAR = "ANONYMAPP_APP_ROOT"
DESKTOP_DATA_ROOT_ENV_VAR = "ANONYMAPP_DESKTOP_DATA_ROOT"
DESKTOP_EXPORT_ROOT_ENV_VAR = "ANONYMAPP_DESKTOP_EXPORT_ROOT"
WINDOWS_APP_DIRNAME = "AnonymApp"
WINDOWS_DESKTOP_DATA_DIRNAME = "desktop"
WINDOWS_EXPORT_DIRNAME = "AnonymApp Exports"


def _resolve_root(env_name: str, default: Path) -> Path:
    raw = os.getenv(env_name)
    if raw:
        return Path(raw).expanduser().resolve()
    return default


def recommended_windows_data_root(local_appdata_root: Path) -> Path:
    return local_appdata_root / WINDOWS_APP_DIRNAME / WINDOWS_DESKTOP_DATA_DIRNAME


def recommended_windows_export_root(user_home_root: Path) -> Path:
    return user_home_root / "Documents" / WINDOWS_EXPORT_DIRNAME


APP_ROOT = _resolve_root(APP_ROOT_ENV_VAR, PROJECT_ROOT)
DESKTOP_DATA_ROOT = _resolve_root(DESKTOP_DATA_ROOT_ENV_VAR, PROJECT_ROOT / "runtime" / "desktop")
DESKTOP_EXPORT_ROOT = _resolve_root(DESKTOP_EXPORT_ROOT_ENV_VAR, DESKTOP_DATA_ROOT / "exports")
DESKTOP_CASES_ROOT = DESKTOP_DATA_ROOT / "cases"
DESKTOP_METADATA_DB = DESKTOP_DATA_ROOT / "metadata.sqlite3"
PACKAGED_MODELS_ROOT = APP_ROOT / "models"


@dataclass(frozen=True)
class DesktopPaths:
    app_root: Path = APP_ROOT
    data_root: Path = DESKTOP_DATA_ROOT
    exports_root: Path = DESKTOP_EXPORT_ROOT
    cases_root: Path = DESKTOP_CASES_ROOT
    metadata_db: Path = DESKTOP_METADATA_DB
    models_root: Path = PACKAGED_MODELS_ROOT


def ensure_desktop_dirs() -> DesktopPaths:
    DESKTOP_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    DESKTOP_EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    DESKTOP_CASES_ROOT.mkdir(parents=True, exist_ok=True)
    return DesktopPaths()
