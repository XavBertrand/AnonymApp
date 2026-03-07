# Phase 0 Research: Windows Desktop Anonymization MVP

## Decision 1: Thin wrappers around existing engines
- Decision: Use one wrapper per existing engine script (`tmp/anonymizer.py`,
  `tmp/transformer_anonymizer.py`) implementing a shared engine interface.
- Rationale: Satisfies engine-reuse and minimal-invasive constitution rules,
  keeps source-of-truth behavior in existing scripts, and avoids logic drift.
- Alternatives considered:
  - Direct UI-to-script calls: rejected due to boundary violations and poor testability.
  - Reimplemented unified anonymizer core: rejected due to high regression risk and constitution conflict.

## Decision 2: Canonical anonymization result model
- Decision: Normalize both backend outputs into a single canonical result with
  required fields: `anonymized_text`, `mapping`, `entities`, `engine_id`,
  `processing_metadata`, optional `pseudonym_metadata`.
- Rationale: Keeps UI and service layers backend-agnostic and supports future
  engines/adapters without changing upper layers.
- Alternatives considered:
  - Backend-specific DTOs in UI layer: rejected due to coupling and switching complexity.
  - Partial normalization only: rejected due to inconsistent deanonymization and audit paths.

## Decision 3: Canonical mapping artifacts in MVP
- Decision: Export/import canonical mapping format only in MVP, with origin
  metadata (`engine_id`, schema version) for compatibility checks.
- Rationale: Simplifies interoperability and validation while preserving ability
  to route deanonymization to originating backend wrapper.
- Alternatives considered:
  - Backend-native mappings only: rejected due to brittle cross-backend UX.
  - Dual export (native + canonical): rejected for MVP complexity; can be added later.

## Decision 4: Windows-first runtime bootstrap and readiness checks
- Decision: Define startup/first-launch readiness validation per backend,
  including runtime dependency checks, model availability checks, and
  non-technical remediation guidance.
- Rationale: End users must not manage Python manually; readiness status must
  fail safely and preserve unaffected backend operation.
- Alternatives considered:
  - Fail lazily on first anonymization attempt only: rejected due to poor UX.
  - Require command-line setup by users: rejected due to product constraints.

## Decision 5: MVP UI scope
- Decision: Implement a minimal CLI-style interface in MVP as UI layer, while
  keeping strict UI/application separation for later desktop GUI replacement.
- Rationale: Delivers core user value quickly with low complexity and complete
  workflow coverage.
- Alternatives considered:
  - Full desktop GUI in MVP: rejected as premature complexity.
  - No UI at all: rejected because MVP requires user-driven workflow.

## Decision 6: Document adapter strategy
- Decision: Implement TXT adapter only in MVP; define adapter contracts for
  future PDF/DOCX/XLSX support without implementing those adapters now.
- Rationale: Matches MVP scope and extensibility requirements.
- Alternatives considered:
  - Implement all formats immediately: rejected due to schedule and risk.
  - Hardcode TXT handling in services: rejected due to architecture erosion.

## Decision 7: Test strategy
- Decision: Require three test layers in MVP: wrapper unit tests, workflow
  integration tests, and mapping compatibility tests.
- Rationale: Protects behavior during wrapper integration and validates
  compatibility/deanonymization invariants.
- Alternatives considered:
  - Integration tests only: rejected because wrapper contract regressions become harder to isolate.
  - Unit tests only: rejected due to end-to-end risks not being covered.

## Decision 8: Dependency management artifact
- Decision: Manage dependencies in a single project dependency manifest and
  lockfile strategy suitable for Windows runtime reproducibility.
- Rationale: Enables deterministic environment setup and easier readiness checks.
- Alternatives considered:
  - Ad hoc installs/documented manual steps: rejected due to non-technical-user constraints.
  - Per-engine separate environments: rejected for operational complexity in MVP.

### Lockfile strategy (explicit)
- Chosen strategy: use `pyproject.toml` as the source dependency manifest and
  use `uv.lock` as the reproducible lockfile artifact for local/runtime
  reproducibility.
- If lockfile refresh is needed, regenerate with `uv` from `pyproject.toml` and
  review dependency deltas before commit.
- If `uv.lock` is temporarily not committed, implementation tasks must still
  document the exact lockfile approach and regeneration command in this section.

## Decision 9: Dependency inventory for existing `tmp` engines
- Decision: Treat dependency inventory below as the MVP baseline for wrapper
  integration and backend readiness checks.
- Rationale: Dependency truth must come from actual imports in
  `tmp/anonymizer.py` and `tmp/transformer_anonymizer.py`.
- Alternatives considered:
  - Manual dependency guessing: rejected due to drift risk.
  - Deferring inventory to implementation: rejected because Phase 0 requires
    explicit dependency confirmation.

### Inventory from `tmp/anonymizer.py`
- Python stdlib: `argparse`, `json`, `logging`, `dataclasses`, `pathlib`,
  `typing`, `urllib.parse`, `re`
- Third-party required for core NER path: `transformers`, `torch` (CPU/GPU
  device resolution), Hugging Face model assets
- Third-party optional path: `requests` (only for optional Ollama QC)
- Optional external service: Ollama HTTP endpoint (non-blocking for core flow)

### Inventory from `tmp/transformer_anonymizer.py`
- Python stdlib: `hashlib`, `re`, `collections`, `typing`
- Third-party required: `transformers`, `rapidfuzz`, `unidecode`
- Third-party conditional: `gliner` (required for GLiNER mode), `torch`
- Internal dependency on classic module symbols:
  `from anonymizer import DATE_RE, EMAIL_RE, IBAN_RE, PHONE_RE, SIREN_SIRET_RE`

### Windows-compatible readiness expectations from inventory
- Backend `classic` is `ready` only when transformers stack and model assets are
  available locally.
- Backend `transformer` is `ready` only when required packages are present and
  GLiNER model assets are available for configured mode.
- Missing `requests` or unavailable Ollama marks optional QC as degraded, but
  MUST NOT block core anonymization.

## Decision 10: Cross-platform preservation at architecture boundaries
- Decision: Keep platform-specific behavior isolated to bootstrap/runtime path
  handling and packaging surfaces; keep core services, adapters, models, and
  engine contracts platform-neutral.
- Verification focus:
  - `src/bootstrap` may contain Windows-first runtime checks and messaging.
  - `src/services`, `src/adapters`, `src/models`, and engine contracts must not
    hardcode Windows-only shell assumptions.
  - Future Linux/macOS support remains possible by replacing boundary-specific
    runtime/bootstrap and packaging components without redesigning core layers.
- Rationale: Preserves FR-020 (future cross-platform option) while maintaining
  Windows-first MVP delivery.
