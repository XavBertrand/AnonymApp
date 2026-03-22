from __future__ import annotations

from pathlib import Path

from src.adapters.documents.registry import DocumentAdapterRegistry
from src.adapters.mappings.canonical_mapping_adapter import CanonicalMappingAdapter
from src.adapters.persistence.artifact_repository import ArtifactRepository
from src.adapters.persistence.database import MetadataDatabase
from src.adapters.persistence.mapping_revision_repository import MappingRevisionRepository
from src.models.canonical_result import CanonicalAnonymizationResult, EntityReplacement, ProcessingMetadata
from src.models.mapping_artifact import MappingArtifact, MappingEntry, MappingOrigin
from src.services.anonymization_service import AnonymizationJobResult

from tests.helpers.desktop_workspace_fakes import (
    FakeAnonymizationService,
    MappingPlanEntry,
    SpyTxtDocumentAdapter,
    build_real_anonymization_service_with_spy,
    build_workspace_service,
)


def test_case_workspace_service_creates_opens_and_batches_documents(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"doc.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    input_path = tmp_path / "doc.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    workspace = service.create_case("Dossier Batch")
    reopened = service.open_case(workspace.case_id)
    batch = service.run_case_anonymization(workspace.case_id, [input_path])

    assert reopened.case_id == workspace.case_id
    assert batch.status == "success"
    assert batch.processed_count == 1
    assert batch.failed_count == 0
    assert batch.workspace.documents[0].status == "success"
    assert Path(batch.items[0].output_path).exists()


def test_workspace_derives_active_revision_from_mapping_revisions_not_case_row(tmp_path: Path) -> None:
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"doc.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
    )
    input_path = tmp_path / "doc.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    workspace = service.create_case("Dossier Drift")
    service.run_case_anonymization(workspace.case_id, [input_path])

    with service._database.connect() as connection:
        connection.execute(
            "UPDATE cases SET active_mapping_revision = 999 WHERE case_id = ?",
            (workspace.case_id,),
        )
        connection.commit()

    reopened = service.open_case(workspace.case_id)

    assert reopened.active_mapping_revision == 1


def test_workspace_uses_runtime_document_adapter_seam(tmp_path: Path) -> None:
    adapter = SpyTxtDocumentAdapter()
    service = build_workspace_service(
        tmp_path,
        anonymization_service=build_real_anonymization_service_with_spy(
            adapter=adapter,
            anonymized_text="<PERSON_1> arrive",
            entities=[],
        ),
        document_registry=DocumentAdapterRegistry([adapter]),
    )
    input_path = tmp_path / "doc.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    workspace = service.create_case("Dossier Seam")
    service.run_case_anonymization(workspace.case_id, [input_path])

    assert input_path in adapter.load_calls
    assert any(path.suffix == ".txt" for path in adapter.save_calls)


class FailingArtifactRepository(ArtifactRepository):
    def create(self, record, *, connection=None):
        raise RuntimeError("artifact write failed")


class UntrustedConflictAnonymizationService(FakeAnonymizationService):
    def run(
        self,
        *,
        backend: str,
        input_path: Path,
        output_path: Path | None = None,
        mapping_path: Path | None = None,
    ) -> AnonymizationJobResult:
        text = input_path.read_text(encoding="utf-8")
        if input_path.name == "first.txt":
            return super().run(
                backend=backend,
                input_path=input_path,
                output_path=output_path,
                mapping_path=mapping_path,
            )

        resolved_output = output_path or input_path.with_suffix(".anon.txt")
        resolved_mapping = mapping_path or input_path.with_suffix(".mapping.json")
        resolved_output.parent.mkdir(parents=True, exist_ok=True)
        anonymized_text = "<PERSON_9> texte libre <PERSON_9>"
        resolved_output.write_text(anonymized_text, encoding="utf-8")
        artifact = MappingArtifact(
            schema_version="1.0",
            mapping_format="canonical-v1",
            origin=MappingOrigin(engine_id=backend),
            entries=[
                MappingEntry(
                    placeholder="<PERSON_9>",
                    original_value="Alice",
                    entity_type="PERSON",
                    position_ranges=[],
                )
            ],
        )
        self._mapping_adapter.dump(artifact, resolved_mapping)
        result = CanonicalAnonymizationResult(
            anonymized_text=anonymized_text,
            mapping={},
            entities=[
                EntityReplacement(
                    entity_type="PERSON",
                    source_value="Alice",
                    replacement_value="<PERSON_9>",
                    offsets_trusted=False,
                )
            ],
            engine_id=backend,
            processing_metadata=ProcessingMetadata(request_id=f"req-{input_path.stem}", duration_ms=1),
        )
        return AnonymizationJobResult(result=result, output_path=resolved_output, mapping_path=resolved_mapping)


def test_workspace_rolls_back_db_state_and_cleans_files_on_mid_flow_failure(tmp_path: Path) -> None:
    database = MetadataDatabase(tmp_path / "desktop.sqlite3")
    mapping_repo = MappingRevisionRepository(database)
    service = build_workspace_service(
        tmp_path,
        plans_by_filename={"doc.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
        database=database,
        mapping_revision_repository=mapping_repo,
        artifact_repository=FailingArtifactRepository(database),
    )
    input_path = tmp_path / "doc.txt"
    input_path.write_text("Alice arrive", encoding="utf-8")

    workspace = service.create_case("Dossier Rollback")
    batch = service.run_case_anonymization(workspace.case_id, [input_path])

    assert batch.status == "failed"
    assert batch.workspace.documents == ()
    assert batch.workspace.artifacts == ()
    assert mapping_repo.get_latest(workspace.case_id) is None
    case_root = service._artifact_store.case_root(workspace.case_id, "Dossier Rollback")
    assert list((case_root / "outputs").glob("*")) == []
    assert list((case_root / "mappings").glob("*")) == []
    assert list((case_root / "imports").glob("*")) == []


def test_workspace_fails_conflicting_document_when_trusted_spans_are_unavailable(tmp_path: Path) -> None:
    database = MetadataDatabase(tmp_path / "desktop.sqlite3")
    mapping_repo = MappingRevisionRepository(database)
    mapping_adapter = CanonicalMappingAdapter()
    service = build_workspace_service(
        tmp_path,
        database=database,
        mapping_revision_repository=mapping_repo,
        mapping_adapter=mapping_adapter,
        plans_by_filename={"first.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
        anonymization_service=UntrustedConflictAnonymizationService(
            mapping_adapter=mapping_adapter,
            plans_by_filename={"first.txt": [MappingPlanEntry("Alice", "<PERSON_1>")]},
        ),
    )

    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("Alice arrive", encoding="utf-8")
    second.write_text("Alice arrive", encoding="utf-8")

    workspace = service.create_case("Dossier Safe Fallback")
    batch = service.run_case_anonymization(workspace.case_id, [first, second])

    assert batch.status == "partial"
    assert batch.items[0].status == "success"
    assert batch.items[1].status == "failed"
    assert "trusted spans" in (batch.items[1].error_summary or "")
    assert batch.workspace.active_mapping_revision == 1
    assert len(batch.workspace.documents) == 1
