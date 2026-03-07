# Data Model: Windows Desktop Anonymization MVP

## 1. AnonymizationJob
- Purpose: Track one anonymization or deanonymization request.
- Fields:
  - `job_id` (string, required)
  - `operation` (enum: `anonymize`, `deanonymize`, required)
  - `input_document` (DocumentAsset, required)
  - `selected_engine_id` (string, required for anonymize)
  - `mapping_artifact_path` (string, required for deanonymize)
  - `status` (enum: `pending`, `running`, `succeeded`, `failed`, required)
  - `error_code` (string, optional)
  - `error_message` (string, optional)
  - `created_at` (datetime, required)
  - `completed_at` (datetime, optional)
- Validation:
  - `selected_engine_id` must reference an available BackendDescriptor.
  - deanonymization requires mapping compatibility validation before run.

## 2. BackendDescriptor
- Purpose: Represent runtime availability and capabilities of a backend engine.
- Fields:
  - `engine_id` (enum-like string: `classic`, `transformer`, required)
  - `display_name` (string, required)
  - `availability_status` (enum: `ready`, `degraded`, `unavailable`, required)
  - `capabilities` (list[string], required)
  - `readiness_checks` (list[ReadinessCheckResult], required)
  - `last_checked_at` (datetime, required)
- Validation:
  - `availability_status=ready` requires all critical checks passing.

## 3. CanonicalAnonymizationResult
- Purpose: Backend-agnostic internal result consumed by app/services/UI.
- Fields:
  - `anonymized_text` (string, required)
  - `mapping` (MappingArtifact, required)
  - `entities` (list[EntityReplacement], required)
  - `engine_id` (string, required)
  - `processing_metadata` (ProcessingMetadata, required)
  - `pseudonym_metadata` (object, optional)
- Validation:
  - `engine_id` must match producing wrapper.
  - `mapping.origin.engine_id` must equal `engine_id`.

## 4. MappingArtifact
- Purpose: Canonical mapping export/import used for deanonymization.
- Fields:
  - `schema_version` (string, required)
  - `origin.engine_id` (string, required)
  - `origin.generated_at` (datetime, required)
  - `entries` (list[MappingEntry], required)
  - `integrity.hash` (string, optional)
- Validation:
  - `schema_version` must be supported by current app.
  - `origin.engine_id` must map to installed/known backend wrapper.

## 5. MappingEntry
- Purpose: One reversible replacement mapping.
- Fields:
  - `placeholder` (string, required)
  - `original_value` (string, required)
  - `entity_type` (string, required)
  - `position_ranges` (list[PositionRange], optional)
- Validation:
  - `placeholder` unique within artifact.

## 6. EntityReplacement
- Purpose: Structured metadata for one anonymized entity occurrence.
- Fields:
  - `entity_type` (string, required)
  - `source_value` (string, required)
  - `replacement_value` (string, required)
  - `confidence` (number, optional)
  - `start_offset` (int, optional)
  - `end_offset` (int, optional)

## 7. DocumentAsset
- Purpose: Represent input/output document metadata.
- Fields:
  - `path` (string, required)
  - `format` (enum: `txt`, required for MVP)
  - `encoding` (string, required)
  - `size_bytes` (integer, required)
- Validation:
  - Must be readable local path for input.
  - format must be `txt` in MVP.

## 8. ProcessingMetadata
- Purpose: Provide auditing context for each run.
- Fields:
  - `request_id` (string, required)
  - `duration_ms` (integer, required)
  - `warnings` (list[string], optional)
  - `optional_services_used` (list[string], optional)
  - `local_only_mode` (boolean, required)

## 9. ReadinessCheckResult
- Purpose: Report startup/dependency validation per backend.
- Fields:
  - `check_name` (string, required)
  - `severity` (enum: `critical`, `warning`, required)
  - `status` (enum: `pass`, `fail`, required)
  - `message` (string, required)
  - `remediation` (string, optional)

## Relationships
- `AnonymizationJob` uses one `BackendDescriptor`.
- `AnonymizationJob` produces one `CanonicalAnonymizationResult`.
- `CanonicalAnonymizationResult` contains one `MappingArtifact` and many
  `EntityReplacement` records.
- `MappingArtifact` contains many `MappingEntry` records.

## State Transitions
- Job state: `pending -> running -> succeeded|failed`.
- Backend availability: `unavailable|degraded -> ready` after successful
  readiness checks, and can regress if checks fail on later startup.
