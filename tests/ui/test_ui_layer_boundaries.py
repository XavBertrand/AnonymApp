from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_widgets_remain_free_of_service_and_persistence_imports() -> None:
    widgets_root = REPO_ROOT / "src" / "app" / "desktop" / "widgets"
    for path in widgets_root.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "src.services" not in text, path.name
        assert "src.adapters.persistence" not in text, path.name


def test_presenter_only_depends_on_case_workspace_facade() -> None:
    presenter_path = REPO_ROOT / "src" / "app" / "desktop" / "presenters" / "workspace_presenter.py"
    text = presenter_path.read_text(encoding="utf-8")

    assert "src.services.case_workspace_service" in text
    assert "src.adapters.persistence" not in text
    assert "mapping_revision_service" not in text
