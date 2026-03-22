from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from src.config.settings import PROJECT_ROOT


def _resolve_root(env_name: str, default: Path) -> Path:
    raw = os.getenv(env_name)
    if raw:
        return Path(raw).expanduser().resolve()
    return default


APP_ROOT = _resolve_root("ANONYMAPP_APP_ROOT", PROJECT_ROOT)
DESKTOP_DATA_ROOT = _resolve_root("ANONYMAPP_DESKTOP_DATA_ROOT", PROJECT_ROOT / "runtime" / "desktop")
DESKTOP_EXPORT_ROOT = _resolve_root("ANONYMAPP_DESKTOP_EXPORT_ROOT", DESKTOP_DATA_ROOT / "exports")
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
