---

description: "Implementation tasks for Windows Desktop Anonymization MVP"

---

# Tasks: Windows Desktop Anonymization MVP

**Input**: Design documents from `/specs/001-build-desktop-anonymizer/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/  
**Tests**: Included per user request (unit, integration, contract).  
**Organization**: Tasks follow implementation plan phases (Phase 0 through Phase 5) with user story labels where applicable.

## Format: `[ID] [Story] Description`

- **[Story]**: User story mapping (`[US1]`, `[US2]`, `[US3]`)
- Include exact file paths in every task

## Constitution Compliance Check

- **Engine Reuse First**: PASS - Tasks keep `./tmp/anonymizer.py` and
  `./tmp/transformer_anonymizer.py` unmodified and implement thin wrappers only
  (`T023`, `T028`).
- **Clear Layered Architecture**: PASS - Tasks enforce explicit layers under
  `src/app`, `src/services`, `src/engines`, `src/adapters`, `src/config`,
  `src/bootstrap`, and `src/models` (`T007`-`T020`).
- **Stable Engine Interface**: PASS - A shared engine contract and wrapper
  compliance tests are required (`T010`, `T021`, `T031`).
- **Incremental Development**: PASS - Tasks are phased from research/foundation
  to backend slices, compatibility, and hardening with checkpoints.
- **Local-First and Privacy**: PASS - Core workflows remain local and optional
  services stay non-blocking (`T024`, `T032`, `T037`).
- **Deterministic and Auditable Outputs**: PASS - Canonical result/mapping
  artifacts and compatibility validation are explicit (`T011`, `T012`, `T015`,
  `T033`, `T035`).
- **Robust Error Handling**: PASS - Readiness states, remediation messaging, and
  failure-path tests are covered (`T018`, `T038`, `T039`).
- **Testability**: PASS - Unit, integration, and contract tests are included
  across wrappers, mappings, and readiness behaviors (`T021`, `T022`, `T026`,
  `T030`, `T035`, `T038`, `T039`).
- **Extensibility**: PASS - Engine/document abstractions and adapter boundaries
  are defined for future growth without core redesign (`T010`, `T014`, `T015`).
- **Minimal Invasive Changes**: PASS - Integration tasks orchestrate existing
  scripts without rewriting anonymization logic (`T023`, `T028`).

## Phase 0: Research and Dependency Confirmation

**Purpose**: Confirm backend/runtime assumptions before coding foundations.

- [X] T001 Confirm dependency inventory for `tmp/anonymizer.py` and `tmp/transformer_anonymizer.py` and record validated package/model requirements in /home/xavier/PycharmProjects/AnonymApp/specs/001-build-desktop-anonymizer/research.md
- [X] T002 Define controlled script-loading approach for non-package `./tmp/*.py` scripts and update wrapper contract details in /home/xavier/PycharmProjects/AnonymApp/specs/001-build-desktop-anonymizer/contracts/engine-interface.md
- [X] T003 Confirm canonical mapping compatibility metadata (`origin.engine_id`, `schema_version`, `origin.generated_at`, `origin.wrapper_contract_version`, `mapping_format`) and finalize these field-level validation rules in /home/xavier/PycharmProjects/AnonymApp/specs/001-build-desktop-anonymizer/contracts/mapping-compatibility.md
- [X] T004 Confirm Windows-first bootstrap and remediation expectations and update executable scenarios in /home/xavier/PycharmProjects/AnonymApp/specs/001-build-desktop-anonymizer/quickstart.md
- [X] T005 Define and document future self-contained Windows packaging requirements (goals, distribution expectations, end-user installation assumptions, and constraints for future packaging work) in /home/xavier/PycharmProjects/AnonymApp/specs/001-build-desktop-anonymizer/quickstart.md
- [X] T006 Verify and document architecture-level cross-platform preservation (isolate platform-specific behavior; avoid unnecessary Windows-only hardcoding in core services/adapters/models/contracts) in /home/xavier/PycharmProjects/AnonymApp/specs/001-build-desktop-anonymizer/research.md

---

## Phase 1: Foundation and Contracts (Blocking)

**Purpose**: Build layered scaffolding, contracts, models, adapters, bootstrap, and storage primitives required by all stories.

- [X] T007 Create project directories and package markers for `src/app/cli`, `src/bootstrap`, `src/services`, `src/engines`, `src/adapters/documents`, `src/adapters/mappings`, `src/models`, `src/config`, `tests/unit`, `tests/integration`, and `tests/contract`
- [X] T008 Create runtime storage directories and bootstrap-safe creation utility in /home/xavier/PycharmProjects/AnonymApp/runtime/outputs, /home/xavier/PycharmProjects/AnonymApp/runtime/mappings, /home/xavier/PycharmProjects/AnonymApp/runtime/logs, and /home/xavier/PycharmProjects/AnonymApp/src/config/settings.py
- [X] T009 Create Windows-compatible dependency manifest in /home/xavier/PycharmProjects/AnonymApp/pyproject.toml and record reproducible environment setup notes in /home/xavier/PycharmProjects/AnonymApp/specs/001-build-desktop-anonymizer/research.md (including explicit lockfile strategy; if lockfile is not committed yet, document the chosen lockfile approach in that section)
- [X] T010 Implement engine interface contract and wrapper base protocol in /home/xavier/PycharmProjects/AnonymApp/src/engines/base.py
- [X] T011 Implement canonical result model in /home/xavier/PycharmProjects/AnonymApp/src/models/canonical_result.py
- [X] T012 Implement mapping artifact model (with origin/schema metadata) in /home/xavier/PycharmProjects/AnonymApp/src/models/mapping_artifact.py
- [X] T013 Implement backend descriptor and readiness models in /home/xavier/PycharmProjects/AnonymApp/src/models/backend_descriptor.py
- [X] T014 Implement TXT document adapter contract and loader/saver in /home/xavier/PycharmProjects/AnonymApp/src/adapters/documents/base.py and /home/xavier/PycharmProjects/AnonymApp/src/adapters/documents/txt_adapter.py
- [X] T015 Implement canonical mapping adapter (serialize/deserialize + schema checks) in /home/xavier/PycharmProjects/AnonymApp/src/adapters/mappings/canonical_mapping_adapter.py
- [X] T016 Implement bootstrap dependency checks in /home/xavier/PycharmProjects/AnonymApp/src/bootstrap/dependency_check.py focused on Python/runtime dependencies and optional services without GPU detection or GPU setup requirements
- [X] T017 Implement bootstrap model availability checks in /home/xavier/PycharmProjects/AnonymApp/src/bootstrap/model_check.py for CPU-only model readiness (no CUDA/MPS/DirectML requirements)
- [X] T018 Implement readiness bootstrap orchestration and user-friendly remediation messages in /home/xavier/PycharmProjects/AnonymApp/src/bootstrap/readiness_bootstrap.py and /home/xavier/PycharmProjects/AnonymApp/src/services/readiness_service.py with explicit CPU-only compatibility reporting
- [X] T019 Implement baseline logging and error translation utilities for local runtime usage in /home/xavier/PycharmProjects/AnonymApp/src/config/logging.py
- [X] T020 Create thin CLI entrypoint and parser routing in /home/xavier/PycharmProjects/AnonymApp/src/app/cli/main.py for `anonymize`, `deanonymize`, and `readiness` commands with backend/input/output/mapping path arguments only (no business logic)

**Checkpoint**: Foundation complete; user story phases can proceed.

---

## Phase 2: MVP Vertical Slice (Backend A)

**Goal**: Deliver TXT anonymization/export workflow through classic backend wrapper.

**Independent Test**: User can anonymize a TXT file with backend A and export anonymized output and canonical mapping.

- [X] T021 [US1] Create contract test for wrapper compliance against engine interface in /home/xavier/PycharmProjects/AnonymApp/tests/contract/test_engine_interface_contract.py
- [X] T022 [US1] Create unit tests for classic wrapper loading/invocation/normalization in /home/xavier/PycharmProjects/AnonymApp/tests/unit/engines/test_classic_wrapper.py, including CPU-only initialization and no-CUDA-required behavior
- [X] T023 [US1] Implement thin classic wrapper with safe loading of `./tmp/anonymizer.py`, explicit CPU execution (Hugging Face `device=-1` where applicable), no GPU auto-detection reliance, and canonical output normalization in /home/xavier/PycharmProjects/AnonymApp/src/engines/classic_wrapper.py
- [X] T024 [US1] Implement anonymization service pipeline (TXT input -> wrapper call -> canonical result -> runtime exports) in /home/xavier/PycharmProjects/AnonymApp/src/services/anonymization_service.py
- [ ] T025 [US1] Extend CLI anonymize command behavior on top of entrypoint/parser to support backend selection and output/mapping export to runtime directories in /home/xavier/PycharmProjects/AnonymApp/src/app/cli/main.py
- [ ] T026 [US1] Add integration test for TXT anonymization with backend A including runtime file exports and successful CPU-only execution on machines without CUDA support in /home/xavier/PycharmProjects/AnonymApp/tests/integration/test_anonymize_txt_backend_a.py

**Checkpoint**: Backend A anonymization flow is functional and testable.

---

## Phase 3: MVP Vertical Slice (Backend B)

**Goal**: Add transformer backend support while preserving identical UI flow and canonical outputs.

**Independent Test**: User can switch to backend B and run same TXT anonymization/export flow without CLI workflow changes.

- [ ] T027 [US1] Create unit tests for transformer wrapper loading/invocation/normalization in /home/xavier/PycharmProjects/AnonymApp/tests/unit/engines/test_transformer_wrapper.py, including CPU-only initialization and no-CUDA-required behavior
- [ ] T028 [US1] Implement thin transformer wrapper with safe loading of `./tmp/transformer_anonymizer.py`, explicit CPU execution for transformers/GLiNER/Torch paths, no GPU auto-detection reliance, and canonical output normalization in /home/xavier/PycharmProjects/AnonymApp/src/engines/transformer_wrapper.py
- [ ] T029 [US1] Extend anonymization service backend registry/selection logic for both wrappers in /home/xavier/PycharmProjects/AnonymApp/src/services/anonymization_service.py
- [ ] T030 [US3] Add integration test for backend switching with unchanged CLI flow and CPU-only backend initialization behavior in /home/xavier/PycharmProjects/AnonymApp/tests/integration/test_anonymize_txt_backend_b.py
- [ ] T031 [US3] Extend contract test assertions to verify parity of canonical fields across both wrappers in /home/xavier/PycharmProjects/AnonymApp/tests/contract/test_engine_interface_contract.py

**Checkpoint**: Both backends support the same anonymization workflow and contract.

---

## Phase 4: Deanonymization and Mapping Compatibility

**Goal**: Deliver canonical mapping import/validation and backend-routed deanonymization.

**Independent Test**: User can deanonymize with valid mapping and receives actionable errors for incompatible mapping.

- [ ] T032 [US2] Implement deanonymization service with mapping compatibility checks and origin-backend routing in /home/xavier/PycharmProjects/AnonymApp/src/services/deanonymization_service.py
- [ ] T033 [US2] Extend canonical mapping adapter to enforce compatibility failure reasons and remediation hints in /home/xavier/PycharmProjects/AnonymApp/src/adapters/mappings/canonical_mapping_adapter.py
- [ ] T034 [US2] Implement CLI deanonymize command using imported canonical mapping artifacts in /home/xavier/PycharmProjects/AnonymApp/src/app/cli/main.py
- [ ] T035 [US2] Add integration tests for mapping export/import roundtrip and incompatible mapping failures in /home/xavier/PycharmProjects/AnonymApp/tests/integration/test_mapping_roundtrip.py

**Checkpoint**: Mapping-driven deanonymization is functional and validated.

---

## Phase 5: Windows Readiness Hardening

**Goal**: Ensure non-technical Windows-first startup validation and graceful degraded operation.

**Independent Test**: App reports readiness states, blocks unavailable backends with remediation, and keeps available backends usable.

- [ ] T036 [US3] Integrate startup readiness bootstrap execution into CLI startup and service initialization flow in /home/xavier/PycharmProjects/AnonymApp/src/app/cli/main.py and /home/xavier/PycharmProjects/AnonymApp/src/services/readiness_service.py with CPU-only readiness expectations
- [ ] T037 [US3] Implement optional service availability checks (e.g., Ollama non-blocking probe) in /home/xavier/PycharmProjects/AnonymApp/src/bootstrap/dependency_check.py and /home/xavier/PycharmProjects/AnonymApp/src/bootstrap/readiness_bootstrap.py without adding GPU checks or GPU setup requirements
- [ ] T038 [US3] Add unit tests for bootstrap dependency/model checks and readiness status transitions in /home/xavier/PycharmProjects/AnonymApp/tests/unit/bootstrap/test_readiness_bootstrap.py, including CPU-only compatibility validation
- [ ] T039 [US3] Add integration tests for missing dependency/model readiness failure behavior with actionable messages and valid operation on standard Windows machines without GPU support in /home/xavier/PycharmProjects/AnonymApp/tests/integration/test_readiness_failures.py
- [ ] T040 [US3] Validate the MVP performance target (<10s for typical TXT files under 1 MB) with a lightweight timed execution procedure and record method/results in /home/xavier/PycharmProjects/AnonymApp/specs/001-build-desktop-anonymizer/quickstart.md (documentation-only; no benchmarking framework)

**Checkpoint**: Windows-first readiness behavior is validated and user-friendly.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 0**: No dependencies; confirms decisions and contract details.
- **Phase 1**: Depends on Phase 0 completion; blocks all feature slices.
- **Phase 2**: Depends on Phase 1; delivers first usable MVP flow (Backend A).
- **Phase 3**: Depends on Phase 2; adds backend B and switching parity.
- **Phase 4**: Depends on Phase 3; adds mapping-driven deanonymization.
- **Phase 5**: Depends on Phase 4; hardens Windows readiness and failure handling.

### User Story Dependencies

- **US1 (Anonymize TXT with selected backend)**: Implemented across Phase 2 and Phase 3.
- **US2 (Deanonymize with mapping)**: Implemented in Phase 4; depends on canonical mapping output from US1.
- **US3 (Switching and error recovery)**: Starts in Phase 3 and completes in Phase 5.

### Within-Phase Execution Rules

- Write/enable tests before or alongside implementation tasks in each phase.
- Implement models/contracts before services/CLI wiring.
- Keep wrappers thin: adapt input, invoke source scripts, normalize outputs, translate errors.
- Enforce CPU-only backend execution; do not rely on CUDA/MPS/DirectML or auto-device behavior.
- Do not modify `tmp/anonymizer.py` or `tmp/transformer_anonymizer.py`.

### Séquençage (sans parallélisme)

- Exécuter les tâches strictement dans l’ordre numérique `T001 -> T040`.
- Ne démarrer aucune tâche suivante tant que la tâche courante n’est pas validée.
- Conserver les checkpoints de phase comme points de validation obligatoires.

---

## Implementation Strategy

### MVP First (Minimum Deliverable)

1. Complete Phase 0 and Phase 1.
2. Complete Phase 2 (Backend A anonymization/export).
3. Validate with T026.
4. Stop for MVP review before enabling full backend switching/deanonymization.

### Incremental Delivery

1. Add Backend B parity (Phase 3).
2. Add deanonymization and compatibility (Phase 4).
3. Add readiness hardening for non-technical Windows users (Phase 5).

### Constraints Enforcement

- No cloud dependencies.
- CPU-only execution path (no required GPU acceleration).
- No complex GUI framework in MVP.
- No distributed architecture.
- No cross-platform packaging work in this task set.
