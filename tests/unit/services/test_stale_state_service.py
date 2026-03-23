from __future__ import annotations

from pathlib import Path

from src.adapters.persistence.artifact_store import ArtifactStore
from src.adapters.persistence.records import ArtifactRecord
from src.models.mapping_artifact import MappingArtifact, MappingEntry, MappingOrigin
from src.services.case_mapping_policy import RevisionMappingEntry, make_mapping_entry_id
from src.services.stale_state_service import StaleStateService


def _artifact_record(tmp_path: Path, *, artifact_id: str, status: str, mapping_revision_used: int) -> ArtifactRecord:
    output_path = tmp_path / f"{artifact_id}.txt"
    mapping_path = tmp_path / f"{artifact_id}.mapping.json"
    output_path.write_text("<PERSON_1> arrive", encoding="utf-8")
    mapping_path.write_text("{}", encoding="utf-8")
    return ArtifactRecord(
        artifact_id=artifact_id,
        case_id="case-1",
        document_id=f"doc-{artifact_id}",
        artifact_type="anonymized_text",
        display_name=f"{artifact_id}.txt",
        file_path=str(output_path),
        created_at=f"2026-03-23T10:00:0{mapping_revision_used}+00:00",
        mapping_revision_used=mapping_revision_used,
        artifact_status=status,
        stale_reason=None,
        supersedes_artifact_id=None,
        preview_snippet="<PERSON_1>",
        job_id=None,
        mapping_path=str(mapping_path),
        content_sha256=ArtifactStore.file_sha256(output_path),
    )


def test_stale_state_service_detects_impacted_artifacts_by_removed_originals(tmp_path: Path) -> None:
    service = StaleStateService()
    impacted = _artifact_record(tmp_path, artifact_id="a1", status="current", mapping_revision_used=1)
    unaffected = _artifact_record(tmp_path, artifact_id="a2", status="current", mapping_revision_used=1)
    mappings = {
        impacted.artifact_id: MappingArtifact(
            schema_version="1.0",
            mapping_format="canonical-v1",
            origin=MappingOrigin(engine_id="transformer"),
            entries=[MappingEntry(placeholder="<PERSON_1>", original_value="Alice", entity_type="PERSON", position_ranges=[(0, 10)])],
        ),
        unaffected.artifact_id: MappingArtifact(
            schema_version="1.0",
            mapping_format="canonical-v1",
            origin=MappingOrigin(engine_id="transformer"),
            entries=[MappingEntry(placeholder="<PERSON_2>", original_value="Bob", entity_type="PERSON", position_ranges=[(0, 8)])],
        ),
    }

    assert service.impacted_artifact_ids(
        artifacts=(unaffected, impacted),
        removed_original_values=("Alice",),
        current_revision_number=2,
        mapping_loader=lambda path: mappings[Path(path).name.split(".")[0]],
    ) == ("a1",)


def test_stale_state_service_requires_trusted_ranges_for_regeneration() -> None:
    service = StaleStateService()
    removed_entries = (
        RevisionMappingEntry(
            mapping_entry_id=make_mapping_entry_id(
                original_value="Alice",
                pseudonym="<PERSON_1>",
                entity_type="PERSON",
                introduced_in_revision=1,
            ),
            original_value="Alice",
            pseudonym="<PERSON_1>",
            entity_type="PERSON",
            introduced_in_revision=1,
            state="removed",
            removed_in_revision=2,
        ),
    )

    allowed, reason = service.regeneration_eligibility(
        artifact_status="stale",
        rewrite_base_trusted=True,
        rewrite_base_issue=None,
        mapping_issue=None,
        removed_entries=removed_entries,
        mapping_artifact=MappingArtifact(
            schema_version="1.0",
            mapping_format="canonical-v1",
            origin=MappingOrigin(engine_id="transformer"),
            entries=[MappingEntry(placeholder="<PERSON_1>", original_value="Alice", entity_type="PERSON", position_ranges=[])],
        ),
        is_latest_for_document=True,
    )

    assert allowed is False
    assert reason is not None
    assert "positions fiables" in reason


def test_stale_state_service_marks_revision_lag_artifact_impacted_when_mapping_is_missing(tmp_path: Path) -> None:
    service = StaleStateService()
    artifact = _artifact_record(tmp_path, artifact_id="a3", status="current", mapping_revision_used=1)
    Path(artifact.mapping_path).unlink()

    assert service.impacted_artifact_ids(
        artifacts=(artifact,),
        removed_original_values=("Alice",),
        current_revision_number=2,
        mapping_loader=lambda path: None,
    ) == ("a3",)


def test_stale_state_service_detects_untrusted_rewrite_base_when_output_is_modified(tmp_path: Path) -> None:
    service = StaleStateService()
    artifact = _artifact_record(tmp_path, artifact_id="a4", status="current", mapping_revision_used=1)
    Path(artifact.file_path).write_text("tampered", encoding="utf-8")

    trust = service.rewrite_base_trust_state(artifact)

    assert trust.trusted is False
    assert trust.issue is not None
    assert "modifiee" in trust.issue


def test_stale_state_service_reports_corrupt_mapping_as_unsafe(tmp_path: Path) -> None:
    service = StaleStateService()
    artifact = _artifact_record(tmp_path, artifact_id="a5", status="current", mapping_revision_used=1)
    Path(artifact.mapping_path).write_text("{not-json", encoding="utf-8")

    mapping_state = service.load_mapping_artifact_state(
        artifact=artifact,
        mapping_loader=lambda path: __import__("json").loads(Path(path).read_text(encoding="utf-8")),
    )
    displayed_status, safety_issue = service.workspace_artifact_status(
        artifact=artifact,
        latest_revision=1,
        output_missing=False,
        rewrite_base_issue=None,
        mapping_issue=mapping_state.issue,
    )

    assert mapping_state.mapping_artifact is None
    assert mapping_state.issue is not None
    assert displayed_status == "unsafe"
    assert safety_issue is not None
