# Implementation Plan: Windows Desktop Anonymization MVP

**Branch**: `001-build-desktop-anonymizer` | **Date**: 2026-03-07 | **Spec**: [/home/xavier/PycharmProjects/AnonymApp/specs/001-build-desktop-anonymizer/spec.md](/home/xavier/PycharmProjects/AnonymApp/specs/001-build-desktop-anonymizer/spec.md)
**Input**: Feature specification from `/specs/001-build-desktop-anonymizer/spec.md`

## Summary

Build a local-first, Windows-first MVP anonymization application that reuses the
existing engines in `./tmp/anonymizer.py` and `./tmp/transformer_anonymizer.py`
through thin wrappers. Deliver incrementally: TXT-only anonymization with both
backends, canonical result normalization, mapping export/import, and
mapping-based deanonymization. Keep architecture layered so a desktop UI can be
added on top of the same application services without backend-specific coupling.
Add an explicit bootstrap layer for Windows-first runtime/dependency/model
readiness without mixing that responsibility into engine wrappers.

## Technical Context

**Language/Version**: Python 3.11 (Windows-compatible)  
**Primary Dependencies**: Existing backend dependencies from `./tmp` scripts, local UI surface (simple CLI for MVP), local config/logging libs  
**Storage**: Local filesystem with explicit runtime storage (`runtime/outputs`, `runtime/mappings`, `runtime/logs`)  
**Testing**: pytest (unit + integration + contract-style adapter tests)  
**Target Platform**: Windows 10/11 desktop (primary), Linux/WSL for development only  
**Project Type**: desktop-app backend core + thin MVP interface (CLI-first)  
**Performance Goals**: TXT anonymization workflow completes in under 10s for typical files (<1 MB) on standard desktop hardware  
**Constraints**: Local-only core workflow, thin wrapper integration only, no cloud dependency, no backend logic rewrite, wrappers load `./tmp` scripts in-place (no move/rewrite), Windows path/process compatibility  
**Scale/Scope**: Single-user desktop MVP; TXT-only document adapter implemented; PDF/DOCX/XLSX prepared as extension points only

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Engine Reuse First: PASS. Existing engines are reused via thin wrappers only; no algorithm rewrite planned.
- Layered Architecture: PASS. Structure separates `ui`, `app/services`, `engines`, `adapters`, `config/storage`.
- Stable Engine Interface: PASS. Both wrappers implement a common internal engine interface and return canonical result.
- Incremental Delivery: PASS. Phase plan delivers runnable increments after each phase.
- Local-First: PASS. Core anonymization and deanonymization are local-only; optional services are non-blocking.
- Deterministic + Auditable: PASS. Canonical result + canonical mapping artifact include metadata for audit and reproducibility.
- Robust Error Handling: PASS. Readiness checks and runtime error translation are first-class phase outputs.
- Testability: PASS. Wrapper, workflow, and mapping compatibility tests are planned in each increment.
- Extensibility: PASS. Adapter/plugin points defined for future engines and document formats.
- Minimal Invasive Changes: PASS. `./tmp` scripts are imported and orchestrated, not moved or rewritten.
  Controlled script-loading is done in wrappers; anonymization logic remains in
  source scripts.

## Project Structure

### Documentation (this feature)

```text
specs/001-build-desktop-anonymizer/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── engine-interface.md
│   ├── canonical-result-schema.md
│   └── mapping-compatibility.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── app/
│   ├── cli/
│   └── ui_contracts/
├── bootstrap/
│   ├── dependency_check.py
│   ├── model_check.py
│   └── readiness_bootstrap.py
├── services/
│   ├── anonymization_service.py
│   ├── deanonymization_service.py
│   └── readiness_service.py
├── engines/
│   ├── base.py
│   ├── classic_wrapper.py
│   └── transformer_wrapper.py
├── adapters/
│   ├── documents/
│   │   ├── base.py
│   │   └── txt_adapter.py
│   └── mappings/
│       └── canonical_mapping_adapter.py
├── models/
│   ├── canonical_result.py
│   ├── mapping_artifact.py
│   └── backend_descriptor.py
└── config/
    ├── settings.py
    └── logging.py

runtime/
├── outputs/
├── mappings/
└── logs/

tests/
├── unit/
│   ├── engines/
│   ├── bootstrap/
│   ├── models/
│   └── adapters/
├── integration/
│   ├── test_anonymize_txt_backend_a.py
│   ├── test_anonymize_txt_backend_b.py
│   ├── test_mapping_roundtrip.py
│   └── test_readiness_failures.py
└── contract/
    └── test_engine_interface_contract.py

tmp/
├── anonymizer.py
└── transformer_anonymizer.py
```

**Structure Decision**: Single Python project with strict layering. MVP uses a
simple CLI in `src/app/cli` to keep UI minimal while preserving UI/application
separation for future desktop UI replacement. Runtime/dependency/model checks
live in `src/bootstrap` only; wrappers remain thin integration adapters.

## Implementation Phases

### Phase 0: Research and Decisions

- Confirm dependency profile of both existing engines and document Windows
  compatibility risks.
- Finalize canonical result schema and canonical mapping policy.
- Finalize thin-wrapper responsibilities and explicit non-responsibilities.
- Finalize Windows runtime bootstrap/readiness strategy for non-technical users.
- Finalize controlled loading strategy for local `./tmp/*.py` scripts without
  moving them or requiring `tmp` to be a formal package.

### Phase 1: Foundation and Contracts

- Create base layer scaffolding and engine abstraction interface.
- Define canonical models and mapping compatibility rules.
- Implement TXT document adapter and storage/config primitives.
- Implement explicit bootstrap layer (`dependency_check`, `model_check`,
  `readiness_bootstrap`) and startup checks.
- Create runtime storage directories and policies for outputs, mappings, logs.

### Phase 2: MVP Vertical Slice (Backend A)

- Implement wrapper for `tmp/anonymizer.py`.
- Implement safe controlled loading/invocation of `tmp/anonymizer.py` from
  wrapper without moving or rewriting source script.
- Wire anonymization service to canonical result pipeline.
- Enable TXT anonymization, preview output, export anonymized text + mapping.
- Add unit/integration tests for wrapper and workflow.

### Phase 3: MVP Vertical Slice (Backend B)

- Implement wrapper for `tmp/transformer_anonymizer.py`.
- Implement safe controlled loading/invocation of
  `tmp/transformer_anonymizer.py` from wrapper without moving or rewriting
  source script.
- Ensure backend switching works with unchanged UI flow.
- Add parity tests against common engine interface and canonical result.

### Phase 4: Deanonymization and Compatibility

- Implement mapping import, compatibility validation, and backend-routed
  deanonymization.
- Add error handling for incompatible mappings and unavailable origin backend.
- Add integration tests for mapping roundtrip and failure scenarios.

### Phase 5: Windows Readiness Hardening

- Implement first-launch bootstrap flow and backend readiness reporting.
- Validate missing dependency/model messaging is actionable and non-technical.
- Confirm no Linux-only assumptions in paths/process handling.
- Confirm bootstrap responsibilities are not duplicated in wrappers/config.

## Post-Design Constitution Re-Check

- Engine wrappers remain thin and logic-preserving: PASS.
- Canonical result boundaries enforced above engine layer: PASS.
- Incremental rollout maintained through phase-by-phase vertical slices: PASS.
- Local-first behavior preserved across anonymization/deanonymization flows: PASS.
- Test coverage planned for wrappers, workflows, and compatibility rules: PASS.
- Bootstrap responsibilities isolated in dedicated layer: PASS.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
