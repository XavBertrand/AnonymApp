from __future__ import annotations

from pathlib import Path

from scripts.packaging.build_windows_portable import launcher_script_content, portable_datas
from scripts.packaging.smoke_test_portable import portable_smoke_report


def test_portable_build_helpers_include_models_and_icon_resources(tmp_path: Path) -> None:
    models_root = tmp_path / "models"
    models_root.mkdir(parents=True)
    (models_root / "model.bin").write_text("ok", encoding="utf-8")
    icon_root = tmp_path / "src" / "app" / "desktop" / "assets"
    icon_root.mkdir(parents=True)
    (icon_root / "a4_desktop.svg").write_text("<svg/>", encoding="utf-8")

    datas = portable_datas(tmp_path)
    launcher = launcher_script_content(tmp_path)

    assert (str(models_root), "models") in datas
    assert (str(icon_root), "assets") in datas
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
