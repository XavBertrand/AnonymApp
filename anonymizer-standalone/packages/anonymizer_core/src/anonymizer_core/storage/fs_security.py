"""Filesystem permission hardening utilities."""

from __future__ import annotations

import os
from pathlib import Path


def ensure_dir_permissions(path: Path, mode: int = 0o700) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, mode)
    except OSError:
        # Best-effort on non-POSIX filesystems (common on Windows).
        pass


def ensure_file_permissions(path: Path, mode: int = 0o600) -> None:
    if path.exists():
        try:
            os.chmod(path, mode)
        except OSError:
            pass
