from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.adapters.mappings.canonical_mapping_adapter import CanonicalMappingAdapter
from src.adapters.persistence.artifact_store import ArtifactStore
from src.adapters.persistence.database import MetadataDatabase
from src.models.backend_descriptor import BackendDescriptor, ReadinessCheckResult
from src.models.canonical_result import CanonicalAnonymizationResult, EntityReplacement, ProcessingMetadata
from src.models.mapping_artifact import MappingArtifact, MappingEntry, MappingOrigin
from src.services.anonymization_service import AnonymizationJobResult
from src.services.case_workspace_service import CaseWorkspaceService
from src.services.readiness_service import ReadinessService


@dataclass(frozen=True)
class MappingPlanEntry:
    original_value: str
    pseudonym: str
    entity_type: str = "PERSON"


class FakeReadinessService(ReadinessService):
    def __init__(self) -> None:
        pass

    def get_readiness_report(self, *, refresh: bool = False) -> list[BackendDescriptor]:
        _ = refresh
        return [
            BackendDescriptor(
                engine_id="transformer",
                display_name="Transformer",
                availability_status="ready",
                readiness_checks=[
                    ReadinessCheckResult(
                        check_name="models",
                        severity="critical",
                        status="pass",
                        message="ready",
                    )
                ],
            )
        ]


class FakeAnonymizationService:
    def __init__(
        self,
        *,
        mapping_adapter: CanonicalMappingAdapter,
        plans_by_filename: dict[str, list[MappingPlanEntry]] | None = None,
        failing_filenames: set[str] | None = None,
    ) -> None:
        self._mapping_adapter = mapping_adapter
        self._plans_by_filename = plans_by_filename or {}
        self._failing_filenames = failing_filenames or set()

    def run(
        self,
        *,
        backend: str,
        input_path: Path,
        output_path: Path | None = None,
        mapping_path: Path | None = None,
    ) -> AnonymizationJobResult:
        if input_path.name in self._failing_filenames:
            raise RuntimeError(f"Configured failure for {input_path.name}")
        text = input_path.read_text(encoding="utf-8")
        plan = self._plans_by_filename.get(input_path.name, [])
        anonymized_text = text
        entities: list[EntityReplacement] = []
        artifact_entries: list[MappingEntry] = []
        for item in plan:
            anonymized_text = anonymized_text.replace(item.original_value, item.pseudonym)
            entities.append(
                EntityReplacement(
                    entity_type=item.entity_type,
                    source_value=item.original_value,
                    replacement_value=item.pseudonym,
                )
            )
            artifact_entries.append(
                MappingEntry(
                    placeholder=item.pseudonym,
                    original_value=item.original_value,
                    entity_type=item.entity_type,
                )
            )

        resolved_output = output_path or input_path.with_suffix(".anon.txt")
        resolved_mapping = mapping_path or input_path.with_suffix(".mapping.json")
        resolved_output.parent.mkdir(parents=True, exist_ok=True)
        resolved_output.write_text(anonymized_text, encoding="utf-8")
        artifact = MappingArtifact(
            schema_version="1.0",
            mapping_format="canonical-v1",
            origin=MappingOrigin(engine_id=backend),
            entries=artifact_entries,
        )
        self._mapping_adapter.dump(artifact, resolved_mapping)
        result = CanonicalAnonymizationResult(
            anonymized_text=anonymized_text,
            mapping={"entries": [item.pseudonym for item in plan]},
            entities=entities,
            engine_id=backend,
            processing_metadata=ProcessingMetadata(request_id=f"req-{input_path.stem}", duration_ms=1),
        )
        return AnonymizationJobResult(result=result, output_path=resolved_output, mapping_path=resolved_mapping)


def build_workspace_service(
    tmp_path: Path,
    *,
    plans_by_filename: dict[str, list[MappingPlanEntry]] | None = None,
    failing_filenames: set[str] | None = None,
) -> CaseWorkspaceService:
    mapping_adapter = CanonicalMappingAdapter()
    artifact_store = ArtifactStore(tmp_path / "cases", tmp_path / "exports")
    database = MetadataDatabase(tmp_path / "desktop.sqlite3")
    anonymization_service = FakeAnonymizationService(
        mapping_adapter=mapping_adapter,
        plans_by_filename=plans_by_filename,
        failing_filenames=failing_filenames,
    )
    return CaseWorkspaceService(
        database=database,
        artifact_store=artifact_store,
        mapping_adapter=mapping_adapter,
        anonymization_service=anonymization_service,
        readiness_service=FakeReadinessService(),
    )
