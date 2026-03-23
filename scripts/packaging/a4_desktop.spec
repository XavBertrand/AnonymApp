# PyInstaller build spec for the A4 desktop workspace.

from __future__ import annotations

from pathlib import Path

from scripts.packaging.build_windows_portable import (
    PORTABLE_EXECUTABLE_NAME,
    portable_build_plan,
    portable_datas,
)

project_root = Path.cwd()
plan = portable_build_plan(project_root)
datas = list(portable_datas(project_root))
icon = str(plan.icon_source) if plan.icon_source is not None and plan.icon_source.suffix.lower() == ".ico" else None


a = Analysis(
    [str(project_root / "src/app/desktop/main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=Path(PORTABLE_EXECUTABLE_NAME).stem,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=icon,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name=plan.bundle_root.name,
)
