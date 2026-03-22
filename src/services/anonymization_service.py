from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.adapters.documents.registry import DocumentAdapterRegistry
from src.adapters.documents.txt_adapter import TxtDocumentAdapter
from src.adapters.mappings.canonical_mapping_adapter import CanonicalMappingAdapter
from src.config.settings import MAPPINGS_DIR, OUTPUTS_DIR, ensure_runtime_dirs
from src.engines.base import EngineInitConfig, EngineWrapper
from src.engines.transformer_wrapper import TransformerWrapper
from src.models.canonical_result import CanonicalAnonymizationResult
from src.models.mapping_artifact import MappingArtifact, MappingEntry, MappingOrigin
from src.services.readiness_service import ReadinessService


@dataclass(frozen=True)
class AnonymizationJobResult:
    result: CanonicalAnonymizationResult
    output_path: Path
    mapping_path: Path


class AnonymizationService:
    def __init__(
        self,
        wrappers: dict[str, EngineWrapper] | None = None,
        document_adapter: TxtDocumentAdapter | None = None,
        document_registry: DocumentAdapterRegistry | None = None,
        mapping_adapter: CanonicalMappingAdapter | None = None,
        readiness_service: ReadinessService | None = None,
    ) -> None:
        using_default_wrappers = wrappers is None
        base_adapter = document_adapter or TxtDocumentAdapter()
        self._wrappers = wrappers or {
            "transformer": TransformerWrapper(),
        }
        self._document_registry = document_registry or DocumentAdapterRegistry([base_adapter])
        self._mapping_adapter = mapping_adapter or CanonicalMappingAdapter()
        self._enforce_readiness = readiness_service is not None or using_default_wrappers
        self._readiness_service = readiness_service or (ReadinessService() if self._enforce_readiness else None)

    def _resolve_wrapper(self, backend: str) -> EngineWrapper:
        wrapper = self._wrappers.get(backend)
        if wrapper is None:
            raise ValueError(f"Unsupported backend '{backend}' for this phase")
        return wrapper

    @staticmethod
    def _default_output_path(input_path: Path, backend: str) -> Path:
        return OUTPUTS_DIR / f"{input_path.stem}.{backend}.anon.txt"

    @staticmethod
    def _default_mapping_path(input_path: Path, backend: str) -> Path:
        return MAPPINGS_DIR / f"{input_path.stem}.{backend}.mapping.json"

    @classmethod
    def _to_mapping_artifact(cls, result: CanonicalAnonymizationResult) -> MappingArtifact:
        entries: list[MappingEntry] = []
        for entity in result.entities:
            placeholder = str(entity.replacement_value).strip()
            original_value = str(entity.source_value).strip()
            entity_type = str(entity.entity_type).strip() or "UNKNOWN"
            if not placeholder:
                continue
            # Safety rule: mapping normalization may only rewrite spans that come from
            # trusted engine offsets. We never synthesize placeholder spans by scanning
            # anonymized text because placeholder-like literals may appear in user content.
            position_ranges: list[tuple[int, int]] = []
            if entity.offsets_trusted and entity.start_offset is not None and entity.end_offset is not None:
                position_ranges = [(entity.start_offset, entity.end_offset)]
            entries.append(
                MappingEntry(
                    placeholder=placeholder,
                    original_value=original_value or placeholder,
                    entity_type=entity_type,
                    position_ranges=position_ranges,
                )
            )

        artifact = MappingArtifact(
            schema_version="1.0",
            mapping_format="canonical-v1",
            origin=MappingOrigin(engine_id=result.engine_id),
            entries=entries,
        )
        artifact.validate()
        return artifact

    def run(
        self,
        *,
        backend: str,
        input_path: Path,
        output_path: Path | None = None,
        mapping_path: Path | None = None,
    ) -> AnonymizationJobResult:
        ensure_runtime_dirs()
        wrapper = self._resolve_wrapper(backend)
        if self._readiness_service is not None:
            self._readiness_service.assert_backend_usable(backend, operation="anonymization")
        wrapper.initialize(config=EngineInitConfig(engine_id=backend, options={}))

        input_adapter = self._document_registry.resolve_for_path(input_path)
        text = input_adapter.load(input_path)

        resolved_output = output_path or self._default_output_path(input_path, backend)
        resolved_mapping = mapping_path or self._default_mapping_path(input_path, backend)

        try:
            output_adapter = self._document_registry.resolve_for_path(resolved_output)
        except ValueError:
            output_adapter = self._document_registry.get(input_adapter.format_name)

        result = wrapper.anonymize(text, options={})
        output_adapter.save(resolved_output, result.anonymized_text)
        artifact = self._to_mapping_artifact(result)
        self._mapping_adapter.dump(artifact, resolved_mapping)
        return AnonymizationJobResult(result=result, output_path=resolved_output, mapping_path=resolved_mapping)


def run_anonymization_job(
    *,
    backend: str,
    input_path: Path,
    output_path: Path | None = None,
    mapping_path: Path | None = None,
) -> AnonymizationJobResult:
    service = AnonymizationService()
    return service.run(
        backend=backend,
        input_path=input_path,
        output_path=output_path,
        mapping_path=mapping_path,
    )
