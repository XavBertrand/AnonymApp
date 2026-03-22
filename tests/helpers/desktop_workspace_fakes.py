from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.adapters.mappings.canonical_mapping_adapter import CanonicalMappingAdapter
from src.adapters.persistence.artifact_store import ArtifactStore
from src.adapters.persistence.database import MetadataDatabase
from src.adapters.documents.registry import DocumentAdapterRegistry
from src.adapters.documents.txt_adapter import TxtDocumentAdapter
from src.engines.base import EngineWrapper
from src.models.backend_descriptor import BackendDescriptor, ReadinessCheckResult
from src.models.canonical_result import CanonicalAnonymizationResult, EntityReplacement, ProcessingMetadata
from src.models.mapping_artifact import MappingArtifact, MappingEntry, MappingOrigin
from src.services.anonymization_service import AnonymizationService
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

    @staticmethod
    def _replace_with_trusted_ranges(text: str, source_value: str, pseudonym: str) -> tuple[str, list[tuple[int, int]]]:
        if not source_value:
            return text, []
        rebuilt: list[str] = []
        ranges: list[tuple[int, int]] = []
        cursor = 0
        output_length = 0
        while True:
            found = text.find(source_value, cursor)
            if found < 0:
                tail = text[cursor:]
                rebuilt.append(tail)
                output_length += len(tail)
                break
            chunk = text[cursor:found]
            rebuilt.append(chunk)
            output_length += len(chunk)
            start = output_length
            rebuilt.append(pseudonym)
            output_length += len(pseudonym)
            ranges.append((start, output_length))
            cursor = found + len(source_value)
        return "".join(rebuilt), ranges

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
            anonymized_text, trusted_ranges = self._replace_with_trusted_ranges(
                anonymized_text,
                item.original_value,
                item.pseudonym,
            )
            entities.append(
                EntityReplacement(
                    entity_type=item.entity_type,
                    source_value=item.original_value,
                    replacement_value=item.pseudonym,
                    start_offset=trusted_ranges[0][0] if len(trusted_ranges) == 1 else None,
                    end_offset=trusted_ranges[0][1] if len(trusted_ranges) == 1 else None,
                    offsets_trusted=len(trusted_ranges) == 1,
                )
            )
            artifact_entries.append(
                MappingEntry(
                    placeholder=item.pseudonym,
                    original_value=item.original_value,
                    entity_type=item.entity_type,
                    position_ranges=trusted_ranges,
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
    anonymization_service=None,
    document_registry: DocumentAdapterRegistry | None = None,
    **service_overrides,
) -> CaseWorkspaceService:
    mapping_adapter = service_overrides.pop("mapping_adapter", CanonicalMappingAdapter())
    artifact_store = ArtifactStore(tmp_path / "cases", tmp_path / "exports")
    database = service_overrides.pop("database", MetadataDatabase(tmp_path / "desktop.sqlite3"))
    document_registry = document_registry or DocumentAdapterRegistry([TxtDocumentAdapter()])
    anonymization_service = anonymization_service or FakeAnonymizationService(
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
        document_registry=document_registry,
        **service_overrides,
    )


class SpyTxtDocumentAdapter(TxtDocumentAdapter):
    def __init__(self) -> None:
        self.load_calls: list[Path] = []
        self.save_calls: list[Path] = []

    def load(self, path: Path) -> str:
        self.load_calls.append(path)
        return super().load(path)

    def save(self, path: Path, content: str) -> None:
        self.save_calls.append(path)
        super().save(path, content)


@dataclass(frozen=True)
class StubWrapperResult:
    anonymized_text: str
    entities: list[EntityReplacement]


class StubEngineWrapper:
    engine_id = "transformer"

    def __init__(self, result: StubWrapperResult) -> None:
        self._result = result

    def initialize(self, config) -> BackendDescriptor:
        _ = config
        return FakeReadinessService().get_readiness_report()[0]

    def anonymize(self, text: str, options: dict | None = None) -> CanonicalAnonymizationResult:
        _ = (text, options)
        return CanonicalAnonymizationResult(
            anonymized_text=self._result.anonymized_text,
            mapping={},
            entities=self._result.entities,
            engine_id="transformer",
            processing_metadata=ProcessingMetadata(request_id="req-stub", duration_ms=1),
        )

    def deanonymize(self, anonymized_text: str, mapping_artifact: MappingArtifact) -> str:
        _ = mapping_artifact
        return anonymized_text

    def readiness_checks(self) -> list[ReadinessCheckResult]:
        return FakeReadinessService().get_readiness_report()[0].readiness_checks


def build_real_anonymization_service_with_spy(
    *,
    adapter: SpyTxtDocumentAdapter,
    anonymized_text: str,
    entities: list[EntityReplacement],
) -> AnonymizationService:
    registry = DocumentAdapterRegistry([adapter])
    wrapper: EngineWrapper = StubEngineWrapper(StubWrapperResult(anonymized_text=anonymized_text, entities=entities))
    return AnonymizationService(
        wrappers={"transformer": wrapper},
        document_registry=registry,
        readiness_service=FakeReadinessService(),
    )
