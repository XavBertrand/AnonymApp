from __future__ import annotations

import pytest

from src.adapters.mappings.canonical_mapping_adapter import MappingCompatibilityError
from src.services.desktop_error_translator import DesktopErrorTranslator
from src.services.readiness_service import ReadinessError


def test_desktop_error_translator_maps_readiness_errors_to_user_message() -> None:
    translator = DesktopErrorTranslator()
    message = translator.translate(
        ReadinessError(
            engine_id="transformer",
            operation="anonymization",
            detail="models missing",
            remediation="Installer les modeles",
        )
    )

    assert "indisponible" in message
    assert "Installer les modeles" in message


def test_desktop_error_translator_maps_mapping_compatibility_errors() -> None:
    translator = DesktopErrorTranslator()
    message = translator.translate(
        MappingCompatibilityError(
            category="invalid_mapping_file",
            detail="broken",
            remediation="Re-export mapping",
        )
    )

    assert "correspondance" in message
    assert "Re-export mapping" in message


def test_case_workspace_service_rethrows_translated_file_errors(tmp_path) -> None:
    from tests.helpers.desktop_workspace_fakes import build_workspace_service

    service = build_workspace_service(tmp_path)

    with pytest.raises(ValueError, match="introuvable"):
        service.open_case("missing-case")
