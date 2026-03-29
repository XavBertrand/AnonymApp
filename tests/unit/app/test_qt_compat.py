from __future__ import annotations

from src.app.desktop import qt_compat


def test_default_qt_platform_does_not_force_offscreen_on_windows(monkeypatch) -> None:
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    monkeypatch.delenv("ANONYMAPP_FORCE_QT_OFFSCREEN", raising=False)
    monkeypatch.setattr(qt_compat.sys, "platform", "win32")

    assert qt_compat._default_qt_platform() is None


def test_default_qt_platform_uses_offscreen_for_pytest_without_display(monkeypatch) -> None:
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    monkeypatch.delenv("ANONYMAPP_FORCE_QT_OFFSCREEN", raising=False)
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setattr(qt_compat.sys, "platform", "linux")
    monkeypatch.setitem(qt_compat.sys.modules, "pytest", object())

    assert qt_compat._default_qt_platform() == "offscreen"
