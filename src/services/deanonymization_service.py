from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.adapters.documents.txt_adapter import TxtDocumentAdapter
from src.adapters.mappings.canonical_mapping_adapter import (
    CanonicalMappingAdapter,
    MappingCompatibilityError,
)
from src.config.settings import OUTPUTS_DIR, ensure_runtime_dirs
from src.engines.base import EngineInitConfig, EngineWrapper
from src.engines.classic_wrapper import ClassicWrapper
from src.engines.transformer_wrapper import TransformerWrapper


@dataclass(frozen=True)
class DeanonymizationJobResult:
    deanonymized_text: str
    output_path: Path
    engine_id: str
    mapping_path: Path


class DeanonymizationService:
    def __init__(
        self,
        wrappers: dict[str, EngineWrapper] | None = None,
        document_adapter: TxtDocumentAdapter | None = None,
        mapping_adapter: CanonicalMappingAdapter | None = None,
    ) -> None:
        self._wrappers = wrappers or {
            "classic": ClassicWrapper(),
            "transformer": TransformerWrapper(),
        }
        self._document_adapter = document_adapter or TxtDocumentAdapter()
        self._mapping_adapter = mapping_adapter or CanonicalMappingAdapter()

    @staticmethod
    def _default_output_path(input_path: Path, backend: str) -> Path:
        return OUTPUTS_DIR / f"{input_path.stem}.{backend}.deanon.txt"

    def _resolve_wrapper(self, backend: str) -> EngineWrapper:
        wrapper = self._wrappers.get(backend)
        if wrapper is None:
            raise MappingCompatibilityError(
                category="unknown_engine_id",
                detail=f"origin.engine_id '{backend}' is not configured in this runtime",
                remediation="Enable/install the origin backend and rerun readiness.",
            )
        return wrapper

    def run(
        self,
        *,
        input_path: Path,
        mapping_path: Path,
        output_path: Path | None = None,
    ) -> DeanonymizationJobResult:
        ensure_runtime_dirs()

        mapping_artifact = self._mapping_adapter.load(mapping_path)
        self._mapping_adapter.validate_compatibility(
            mapping_artifact,
            supported_engine_ids=set(self._wrappers.keys()),
        )

        backend = mapping_artifact.origin.engine_id
        wrapper = self._resolve_wrapper(backend)

        descriptor = wrapper.initialize(EngineInitConfig(engine_id=backend, options={}))
        self._mapping_adapter.validate_origin_backend_availability(
            engine_id=backend,
            availability_status=descriptor.availability_status,
        )

        anonymized_text = self._document_adapter.load(input_path)
        deanonymized_text = wrapper.deanonymize(anonymized_text, mapping_artifact)

        resolved_output = output_path or self._default_output_path(input_path, backend)
        self._document_adapter.save(resolved_output, deanonymized_text)

        return DeanonymizationJobResult(
            deanonymized_text=deanonymized_text,
            output_path=resolved_output,
            engine_id=backend,
            mapping_path=mapping_path,
        )


def run_deanonymization_job(
    *,
    input_path: Path,
    mapping_path: Path,
    output_path: Path | None = None,
) -> DeanonymizationJobResult:
    service = DeanonymizationService()
    return service.run(
        input_path=input_path,
        mapping_path=mapping_path,
        output_path=output_path,
    )
