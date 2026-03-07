# Contract: Engine Wrapper Interface

## Purpose
Define the common contract implemented by thin wrappers around existing engines.

## Methods
- `initialize(config) -> BackendDescriptor`
- `anonymize(text, options) -> CanonicalAnonymizationResult`
- `deanonymize(anonymized_text, mapping_artifact) -> str`
- `readiness_checks() -> list[ReadinessCheckResult]`

## Invariants
- Wrappers MUST only adapt/invoke/normalize/translate errors.
- Wrappers MUST NOT duplicate anonymization logic from source scripts.
- Returned anonymization output MUST always be canonical.
- Wrapper MUST include `engine_id` in canonical result.
