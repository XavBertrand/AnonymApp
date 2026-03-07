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
