from __future__ import annotations

from pathlib import Path

from scripts.packaging.build_windows_portable import (
    launcher_script_content,
    portable_datas,
    portable_hiddenimports,
    portable_runtime_binaries,
)
from scripts.packaging.smoke_test_portable import portable_smoke_report


def test_portable_build_helpers_include_models_and_icon_resources(tmp_path: Path) -> None:
    models_root = tmp_path / "models"
    models_root.mkdir(parents=True)
    (models_root / "model.bin").write_text("ok", encoding="utf-8")
    icon_root = tmp_path / "src" / "app" / "desktop" / "assets"
    icon_root.mkdir(parents=True)
    (icon_root / "a4_desktop.svg").write_text("<svg/>", encoding="utf-8")
    tmp_root = tmp_path / "tmp"
    tmp_root.mkdir(parents=True)
    (tmp_root / "anonymizer.py").write_text("# stub\n", encoding="utf-8")
    (tmp_root / "transformer_anonymizer.py").write_text("# stub\n", encoding="utf-8")

    datas = portable_datas(tmp_path)
    hiddenimports = portable_hiddenimports()
    launcher = launcher_script_content(tmp_path)

    assert (str(models_root), "models") in datas
    assert (str(icon_root), "assets") in datas
    assert (str(tmp_root / "anonymizer.py"), "tmp") in datas
    assert (str(tmp_root / "transformer_anonymizer.py"), "tmp") in datas
    assert "transformers" in hiddenimports
    assert "torch" in hiddenimports
    assert "rapidfuzz" in hiddenimports
    assert "unidecode" in hiddenimports
    assert "gliner" in hiddenimports
    assert "requests" in hiddenimports
    assert "ANONYMAPP_APP_ROOT" in launcher
    assert "ANONYMAPP_DESKTOP_EXPORT_ROOT" in launcher


def test_windows_portable_smoke_report_is_ready_for_valid_extracted_layout(tmp_path: Path) -> None:
    models_root = tmp_path / "models"
    models_root.mkdir(parents=True)
    (models_root / "model.bin").write_text("ok", encoding="utf-8")

    report = portable_smoke_report(tmp_path)

    assert all(state == "ready" for state, _message in report.values())
    assert "deanonymized" in report["deanonymized_export"][1]
    assert "review" in report["regenerated_naming"][1]


def test_portable_runtime_binaries_include_conda_runtime_dlls(monkeypatch, tmp_path: Path) -> None:
    conda_prefix = tmp_path / "miniforge3" / "envs" / "desktop"
    runtime_root = conda_prefix / "Library" / "bin"
    runtime_root.mkdir(parents=True)
    for dll_name in ("sqlite3.dll", "libcrypto-3-x64.dll", "libssl-3-x64.dll"):
        (runtime_root / dll_name).write_text("dll", encoding="utf-8")

    monkeypatch.setenv("CONDA_PREFIX", str(conda_prefix))
    monkeypatch.setattr(
        "scripts.packaging.build_windows_portable._is_windows_build_host",
        lambda: True,
    )

    binaries = portable_runtime_binaries(tmp_path)

    assert (str(runtime_root / "sqlite3.dll"), ".") in binaries
    assert (str(runtime_root / "libcrypto-3-x64.dll"), ".") in binaries
    assert (str(runtime_root / "libssl-3-x64.dll"), ".") in binaries
