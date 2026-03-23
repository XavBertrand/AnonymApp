from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_rewrite_logic_remains_centralized_in_mapping_rewrite_support() -> None:
    policy_text = (REPO_ROOT / "src" / "services" / "case_mapping_policy.py").read_text(encoding="utf-8")
    review_text = (REPO_ROOT / "src" / "services" / "substitution_review_service.py").read_text(encoding="utf-8")
    regen_text = (REPO_ROOT / "src" / "services" / "stale_output_regeneration_service.py").read_text(encoding="utf-8")

    assert "from src.services.mapping_rewrite_support import" in policy_text
    assert "rewrite_artifact_for_removed_entries" in review_text
    assert "rewrite_artifact_for_removed_entries" in regen_text
    assert "TextRewrite(" not in review_text
    assert "TextRewrite(" not in regen_text


def test_workspace_facade_does_not_own_rewrite_logic() -> None:
    workspace_text = (REPO_ROOT / "src" / "services" / "case_workspace_service.py").read_text(encoding="utf-8")

    assert "rewrite_artifact_for_removed_entries" not in workspace_text
    assert "apply_text_rewrites" not in workspace_text
