"""Document anonymization orchestration service for standalone text outputs."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from pathlib import Path

from anonymizer_core.detectors.ner_detector import NERUnavailableError, NerDetector
from anonymizer_core.detectors.regex_detector import RegexDetector
from anonymizer_core.detectors.rule_detector import RuleDetector
from anonymizer_core.errors import InputValidationError, ProcessingError, SecurityPolicyError
from anonymizer_core.models import BatchRequest, BatchResult, DocumentRequest, DocumentResult, Entity, ParsedDocument
from anonymizer_core.parsers.docx_parser import DocxParser
from anonymizer_core.parsers.pdf_parser import PdfParser
from anonymizer_core.parsers.txt_parser import TxtParser
from anonymizer_core.parsers.xlsx_parser import XlsxParser
from anonymizer_core.placeholders import PlaceholderGenerator, normalize_entity_value
from anonymizer_core.safe_logging import get_logger, log_safe, sanitize_exception
from anonymizer_core.storage.audit_store import AuditStore
from anonymizer_core.storage.fs_security import ensure_dir_permissions, ensure_file_permissions
from anonymizer_core.storage.mapping_store import MappingStore
from anonymizer_core.streaming import enforce_limits

_AMBIGUOUS_RE = re.compile(r"\b(M\.|Mme|Mr|Dr)\s+[A-Z]", re.I)


def _doc_id(path: Path) -> str:
    digest = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:10]
    return f"doc-{digest}"


def _ext(path: Path) -> str:
    return path.suffix.lower().lstrip(".")


def _apply_replacements(text: str, replacements: dict[str, str]) -> str:
    for source in sorted(replacements.keys(), key=len, reverse=True):
        text = text.replace(source, replacements[source])
    return text


def _build_replacements(entities: list[Entity], generator: PlaceholderGenerator) -> dict[str, str]:
    dedup: dict[tuple[str, str], str] = {}
    for entity in entities:
        value = entity.value.strip()
        if not value:
            continue
        key = (entity.entity_type.lower(), normalize_entity_value(value))
        dedup[key] = value

    replacements: dict[str, str] = {}
    for entity_type, normalized in sorted(dedup.keys()):
        original = dedup[(entity_type, normalized)]
        replacements[original] = generator.generate(entity_type, original)
    return replacements


def _flatten_output_name(input_path: Path, input_root: Path) -> str:
    try:
        rel = input_path.relative_to(input_root)
        stem_parts = list(rel.parts)
    except ValueError:
        stem_parts = [input_path.name]
    safe = "__".join(part.replace(" ", "_") for part in stem_parts)
    safe = safe.replace(".", "_")
    return f"{safe}.txt"


class DocumentAnonymizer:
    """Batch-oriented anonymizer service with per-document isolation."""

    def __init__(self, mapping_store: MappingStore | None = None) -> None:
        self.logger = get_logger()
        self._parsers = {
            "txt": TxtParser(),
            "pdf": PdfParser(),
            "docx": DocxParser(),
            "xlsx": XlsxParser(),
        }
        self._regex = RegexDetector()
        self._ner = NerDetector()
        self._rules = RuleDetector()
        self._mapping_store = mapping_store or MappingStore()

    def _detect_entities(self, parsed: ParsedDocument, request: DocumentRequest, warning_codes: list[str]) -> list[Entity]:
        entities: list[Entity] = []
        if parsed.text.strip() == "":
            return entities

        if request.policy.enable_ner:
            try:
                entities.extend(self._ner.detect(parsed.text, parsed.document_id))
            except NERUnavailableError:
                warning_codes.append("NER_UNAVAILABLE")

        if request.policy.enable_regex:
            entities.extend(self._regex.detect(parsed.text, parsed.document_id))
        if request.policy.enable_rules:
            entities.extend(self._rules.detect(parsed.text, parsed.document_id))

        if _AMBIGUOUS_RE.search(parsed.text):
            warning_codes.append("AMBIGUOUS_ENTITY")

        by_identity: dict[tuple[str, str, str], Entity] = {}
        for entity in entities:
            key = (entity.entity_type, normalize_entity_value(entity.value), entity.span_id)
            by_identity[key] = entity
        return list(by_identity.values())

    def _anonymize_document_with_generator(
        self,
        request: DocumentRequest,
        placeholder_generator: PlaceholderGenerator,
    ) -> tuple[DocumentResult, dict[str, str], str]:
        input_path = request.input_path
        extension = request.format_hint or _ext(input_path)
        document_id = _doc_id(input_path)

        if extension not in self._parsers:
            raise InputValidationError(f"Unsupported format: {extension}")

        warning_codes: list[str] = []
        try:
            parsed = self._parsers[extension].parse(input_path, document_id)
            entities = self._detect_entities(parsed, request, warning_codes)
            replacements = _build_replacements(entities, placeholder_generator)
            anonymized_text = _apply_replacements(parsed.text, replacements)

            request.output_path.parent.mkdir(parents=True, exist_ok=True)
            request.output_path.write_text(anonymized_text, encoding="utf-8")
            ensure_file_permissions(request.output_path, request.policy.storage_permissions_file)

            status = "degraded" if warning_codes else "succeeded"
            return (
                DocumentResult(
                    document_id=document_id,
                    source_path=str(input_path),
                    status=status,
                    output_path=str(request.output_path),
                    warning_codes=warning_codes,
                    mapping_size=len(replacements),
                ),
                replacements,
                anonymized_text,
            )
        except Exception as exc:  # noqa: BLE001
            safe = sanitize_exception(exc)
            raise ProcessingError(safe) from exc

    def anonymize_batch(self, request: BatchRequest) -> BatchResult:
        if request.policy.allow_network:
            raise SecurityPolicyError("Standalone mode requires strict_offline policy")

        ensure_dir_permissions(request.output_root, request.policy.storage_permissions_dir)
        output_anonymized = request.output_root / "anonymized_txt"
        ensure_dir_permissions(output_anonymized, request.policy.storage_permissions_dir)

        enforce_limits(
            request.input_paths,
            max_docs=request.policy.max_documents_per_batch,
            max_total_mb=request.policy.max_total_input_mb,
            max_pages_per_document=request.policy.max_pages_per_document,
        )

        trace_id = str(uuid.uuid4())
        audit_store = AuditStore(
            output_root=request.output_root,
            dir_mode=request.policy.storage_permissions_dir,
            file_mode=request.policy.storage_permissions_file,
        )

        results: list[DocumentResult] = []
        failed = 0
        degraded = 0
        placeholder_generator = PlaceholderGenerator(
            case_id=request.case_id,
            schema_version=request.policy.mapping_schema_version,
        )

        mapping_documents: list[dict[str, object]] = []
        concat_chunks: list[str] = []

        for input_path in request.input_paths:
            try:
                out_name = _flatten_output_name(input_path, request.input_root)
                out_path = output_anonymized / out_name
                doc_request = DocumentRequest(
                    case_id=request.case_id,
                    policy=request.policy,
                    input_path=input_path,
                    output_path=out_path,
                    format_hint=_ext(input_path),
                )
                doc_result, replacements, anonymized_text = self._anonymize_document_with_generator(
                    doc_request,
                    placeholder_generator,
                )
                mapping_documents.append(
                    {
                        "document_id": doc_result.document_id,
                        "source_path": str(input_path),
                        "output_txt": str(out_path),
                        "replacements": replacements,
                    }
                )
                results.append(doc_result)
                if doc_result.status == "degraded":
                    degraded += 1
                if doc_result.warning_codes:
                    audit_store.append(
                        case_id=request.case_id,
                        event_code="doc_degraded",
                        trace_id=trace_id,
                        document_id=doc_result.document_id,
                        safe_metadata={"warning_codes": list(doc_result.warning_codes)},
                    )
                if request.concat_output:
                    concat_chunks.append(f"# {input_path.name}\n{anonymized_text}\n")
            except ProcessingError as exc:
                failed += 1
                doc_result = DocumentResult(
                    document_id=_doc_id(input_path),
                    source_path=str(input_path),
                    status="failed",
                    output_path=None,
                    failure_code=exc.code,
                    failure_message_safe=exc.message_safe,
                )
                results.append(doc_result)
                log_safe(self.logger, 30, "document_failed", code=exc.code)
                audit_store.append(
                    case_id=request.case_id,
                    event_code="doc_failed",
                    trace_id=trace_id,
                    document_id=doc_result.document_id,
                    safe_metadata={"failure_code": exc.code},
                )
                if not request.continue_on_error:
                    break

        mapping_path = self._mapping_store.write_mapping(
            case_id=request.case_id,
            schema_version=request.policy.mapping_schema_version,
            documents=mapping_documents,
            output_root=request.output_root,
            file_mode=request.policy.storage_permissions_file,
            dir_mode=request.policy.storage_permissions_dir,
        )

        concat_output_path: str | None = None
        if request.concat_output:
            concat_path = request.output_root / request.concat_filename
            concat_path.write_text("\n".join(concat_chunks), encoding="utf-8")
            ensure_file_permissions(concat_path, request.policy.storage_permissions_file)
            concat_output_path = str(concat_path)

        totals = {
            "total_documents": len(request.input_paths),
            "succeeded": len([r for r in results if r.status == "succeeded"]),
            "failed": failed,
            "degraded": degraded,
        }
        status = "completed" if failed == 0 else "completed_with_errors"
        report_payload = {
            "schema_version": request.policy.report_schema_version,
            "mapping_schema_version": request.policy.mapping_schema_version,
            "case_id": request.case_id,
            "policy": request.policy_name,
            "totals": totals,
            "documents": [r.__dict__ for r in results],
            "trace_id": trace_id,
            "mapping_path": str(mapping_path),
            "concat_output_path": concat_output_path,
        }
        request.report_path.parent.mkdir(parents=True, exist_ok=True)
        request.report_path.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")
        ensure_file_permissions(request.report_path, request.policy.storage_permissions_file)

        return BatchResult(
            case_id=request.case_id,
            status=status,
            totals=totals,
            documents=results,
            report_path=str(request.report_path),
            mapping_path=str(mapping_path),
            concat_output_path=concat_output_path,
        )
