# Contract: Mapping Compatibility and Deanonymization

## Export Policy
- MVP exports canonical mapping artifacts only.

## Required Metadata
- `schema_version`
- `origin.engine_id`
- `origin.generated_at`
- `origin.wrapper_contract_version`
- `mapping_format` (expected value for MVP: `canonical-v1`)

## Validation Workflow
1. Validate schema version support.
2. Validate required metadata exists.
3. Validate `mapping_format` matches supported canonical format.
4. Validate `origin.engine_id` is one of supported backend IDs.
5. Validate origin engine wrapper is available and `ready`/`degraded` for
   deanonymization path.
6. Route deanonymization through origin engine wrapper.

## Failure Behavior
- If any validation fails, operation must stop with actionable error.
- System must not produce partial or guessed deanonymized output.
- Compatibility failures must return explicit remediation category:
  - `unsupported_schema_version`
  - `unknown_engine_id`
  - `missing_required_metadata`
  - `unsupported_mapping_format`
  - `origin_backend_unavailable`
