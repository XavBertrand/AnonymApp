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

## Controlled Script Loading Strategy (`./tmp/*.py`)
- Source files `tmp/anonymizer.py` and `tmp/transformer_anonymizer.py` remain
  in place and are not rewritten by wrapper integration.
- Wrappers MUST load local scripts via controlled module loading (for example
  `importlib`-based file loading) and MUST NOT assume `tmp` is an installed
  package.
- Wrappers MUST register deterministic module names for runtime consistency:
  - `classic_wrapper` loads `tmp/anonymizer.py` as module name `anonymizer`.
  - `transformer_wrapper` loads `tmp/transformer_anonymizer.py` after ensuring
    `anonymizer` symbols are available for its internal import dependency.
- Loading failures (file missing, import error, dependency missing) MUST be
  translated into user-facing readiness/runtime errors without leaking raw stack
  traces to end users.
- Wrapper responsibility boundary is strict:
  - Adapt wrapper input to source module call shape.
  - Invoke source module functions/classes.
  - Normalize backend output to canonical result.
  - Translate/annotate errors for higher layers.
