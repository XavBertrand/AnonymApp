from __future__ import annotations

from scripts.packaging.smoke_test_portable import packaged_models_root, packaged_readiness


def test_packaged_readiness_is_blocked_when_models_dir_is_missing(tmp_path) -> None:
    status, message = packaged_readiness(tmp_path)

    assert status == "blocked"
    assert "not found" in message
    assert packaged_models_root(tmp_path).name == "models"


def test_packaged_readiness_is_ready_when_models_dir_contains_files(tmp_path) -> None:
    models_root = packaged_models_root(tmp_path)
    models_root.mkdir(parents=True)
    (models_root / "model.bin").write_text("ok", encoding="utf-8")

    status, message = packaged_readiness(tmp_path)

    assert status == "ready"
    assert str(models_root) in message
