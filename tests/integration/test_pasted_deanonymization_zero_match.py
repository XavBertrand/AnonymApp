from __future__ import annotations

from tests.helpers.desktop_workspace_fakes import build_workspace_service


def test_pasted_deanonymization_zero_match_returns_unchanged_text(tmp_path) -> None:
    service = build_workspace_service(tmp_path)
    workspace = service.create_case("Dossier Aucun Match")

    session = service.deanonymize_pasted_text(workspace.case_id, "<PERSON_404> reste masque")

    assert session.result_state == "no_match"
    assert session.match_count == 0
    assert session.result_text == "<PERSON_404> reste masque"
    assert "Aucune correspondance" in session.status_message
