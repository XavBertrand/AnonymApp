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

## Phase 0: Research and Dependency Confirmation

**Purpose**: Confirm backend/runtime assumptions before coding foundations.

- [ ] T001 Confirm dependency inventory for `tmp/anonymizer.py` and `tmp/transformer_anonymizer.py` and record validated package/model requirements in /home/xavier/PycharmProjects/AnonymApp/specs/001-build-desktop-anonymizer/research.md
- [ ] T002 Define controlled script-loading approach for non-package `./tmp/*.py` scripts and update wrapper contract details in /home/xavier/PycharmProjects/AnonymApp/specs/001-build-desktop-anonymizer/contracts/engine-interface.md
- [ ] T003 Confirm canonical mapping compatibility metadata (`engine_id`, `schema_version`) and finalize validation rules in /home/xavier/PycharmProjects/AnonymApp/specs/001-build-desktop-anonymizer/contracts/mapping-compatibility.md
- [ ] T004 Confirm Windows-first bootstrap and remediation expectations and update executable scenarios in /home/xavier/PycharmProjects/AnonymApp/specs/001-build-desktop-anonymizer/quickstart.md

---

## Phase 1: Foundation and Contracts (Blocking)

**Purpose**: Build layered scaffolding, contracts, models, adapters, bootstrap, and storage primitives required by all stories.

- [ ] T005 Create project directories and package markers for `src/app/cli`, `src/bootstrap`, `src/services`, `src/engines`, `src/adapters/documents`, `src/adapters/mappings`, `src/models`, `src/config`, `tests/unit`, `tests/integration`, and `tests/contract`
- [ ] T006 Create runtime storage directories and bootstrap-safe creation utility in /home/xavier/PycharmProjects/AnonymApp/runtime/outputs, /home/xavier/PycharmProjects/AnonymApp/runtime/mappings, /home/xavier/PycharmProjects/AnonymApp/runtime/logs, and /home/xavier/PycharmProjects/AnonymApp/src/config/settings.py
- [ ] T007 Create Windows-compatible dependency manifest and reproducible environment setup in /home/xavier/PycharmProjects/AnonymApp/pyproject.toml with dependencies for `./tmp` engines and app layers, plus lockfile workflow notes for MVP reproducibility
- [ ] T008 Implement engine interface contract and wrapper base protocol in /home/xavier/PycharmProjects/AnonymApp/src/engines/base.py
- [ ] T009 Implement canonical result model in /home/xavier/PycharmProjects/AnonymApp/src/models/canonical_result.py
- [ ] T010 Implement mapping artifact model (with origin/schema metadata) in /home/xavier/PycharmProjects/AnonymApp/src/models/mapping_artifact.py
- [ ] T011 Implement backend descriptor and readiness models in /home/xavier/PycharmProjects/AnonymApp/src/models/backend_descriptor.py
- [ ] T012 Implement TXT document adapter contract and loader/saver in /home/xavier/PycharmProjects/AnonymApp/src/adapters/documents/base.py and /home/xavier/PycharmProjects/AnonymApp/src/adapters/documents/txt_adapter.py
- [ ] T013 Implement canonical mapping adapter (serialize/deserialize + schema checks) in /home/xavier/PycharmProjects/AnonymApp/src/adapters/mappings/canonical_mapping_adapter.py
- [ ] T014 Implement bootstrap dependency checks in /home/xavier/PycharmProjects/AnonymApp/src/bootstrap/dependency_check.py
- [ ] T015 Implement bootstrap model availability checks in /home/xavier/PycharmProjects/AnonymApp/src/bootstrap/model_check.py
- [ ] T016 Implement readiness bootstrap orchestration and user-friendly remediation messages in /home/xavier/PycharmProjects/AnonymApp/src/bootstrap/readiness_bootstrap.py and /home/xavier/PycharmProjects/AnonymApp/src/services/readiness_service.py
- [ ] T017 Implement baseline logging and error translation utilities for local runtime usage in /home/xavier/PycharmProjects/AnonymApp/src/config/logging.py
- [ ] T018 Create thin CLI entrypoint and parser routing in /home/xavier/PycharmProjects/AnonymApp/src/app/cli/main.py for `anonymize`, `deanonymize`, and `readiness` commands with backend/input/output/mapping path arguments only (no business logic)

**Checkpoint**: Foundation complete; user story phases can proceed.

---

## Phase 2: MVP Vertical Slice (Backend A)

**Goal**: Deliver TXT anonymization/export workflow through classic backend wrapper.

**Independent Test**: User can anonymize a TXT file with backend A and export anonymized output and canonical mapping.

- [ ] T019 [US1] Create contract test for wrapper compliance against engine interface in /home/xavier/PycharmProjects/AnonymApp/tests/contract/test_engine_interface_contract.py
- [ ] T020 [US1] Create unit tests for classic wrapper loading/invocation/normalization in /home/xavier/PycharmProjects/AnonymApp/tests/unit/engines/test_classic_wrapper.py
- [ ] T021 [US1] Implement thin classic wrapper with safe loading of `./tmp/anonymizer.py` and canonical output normalization in /home/xavier/PycharmProjects/AnonymApp/src/engines/classic_wrapper.py
- [ ] T022 [US1] Implement anonymization service pipeline (TXT input -> wrapper call -> canonical result -> runtime exports) in /home/xavier/PycharmProjects/AnonymApp/src/services/anonymization_service.py
- [ ] T023 [US1] Extend CLI anonymize command behavior on top of entrypoint/parser to support backend selection and output/mapping export to runtime directories in /home/xavier/PycharmProjects/AnonymApp/src/app/cli/main.py
- [ ] T024 [US1] Add integration test for TXT anonymization with backend A including runtime file exports in /home/xavier/PycharmProjects/AnonymApp/tests/integration/test_anonymize_txt_backend_a.py

**Checkpoint**: Backend A anonymization flow is functional and testable.

---

## Phase 3: MVP Vertical Slice (Backend B)

**Goal**: Add transformer backend support while preserving identical UI flow and canonical outputs.

**Independent Test**: User can switch to backend B and run same TXT anonymization/export flow without CLI workflow changes.

- [ ] T025 [US1] Create unit tests for transformer wrapper loading/invocation/normalization in /home/xavier/PycharmProjects/AnonymApp/tests/unit/engines/test_transformer_wrapper.py
- [ ] T026 [US1] Implement thin transformer wrapper with safe loading of `./tmp/transformer_anonymizer.py` and canonical output normalization in /home/xavier/PycharmProjects/AnonymApp/src/engines/transformer_wrapper.py
- [ ] T027 [US1] Extend anonymization service backend registry/selection logic for both wrappers in /home/xavier/PycharmProjects/AnonymApp/src/services/anonymization_service.py
- [ ] T028 [US3] Add integration test for backend switching with unchanged CLI flow in /home/xavier/PycharmProjects/AnonymApp/tests/integration/test_anonymize_txt_backend_b.py
- [ ] T029 [US3] Extend contract test assertions to verify parity of canonical fields across both wrappers in /home/xavier/PycharmProjects/AnonymApp/tests/contract/test_engine_interface_contract.py

**Checkpoint**: Both backends support the same anonymization workflow and contract.

---

## Phase 4: Deanonymization and Mapping Compatibility

**Goal**: Deliver canonical mapping import/validation and backend-routed deanonymization.

**Independent Test**: User can deanonymize with valid mapping and receives actionable errors for incompatible mapping.

- [ ] T030 [US2] Implement deanonymization service with mapping compatibility checks and origin-backend routing in /home/xavier/PycharmProjects/AnonymApp/src/services/deanonymization_service.py
- [ ] T031 [US2] Extend canonical mapping adapter to enforce compatibility failure reasons and remediation hints in /home/xavier/PycharmProjects/AnonymApp/src/adapters/mappings/canonical_mapping_adapter.py
- [ ] T032 [US2] Implement CLI deanonymize command using imported canonical mapping artifacts in /home/xavier/PycharmProjects/AnonymApp/src/app/cli/main.py
- [ ] T033 [US2] Add integration tests for mapping export/import roundtrip and incompatible mapping failures in /home/xavier/PycharmProjects/AnonymApp/tests/integration/test_mapping_roundtrip.py

**Checkpoint**: Mapping-driven deanonymization is functional and validated.

---

## Phase 5: Windows Readiness Hardening

**Goal**: Ensure non-technical Windows-first startup validation and graceful degraded operation.

**Independent Test**: App reports readiness states, blocks unavailable backends with remediation, and keeps available backends usable.

- [ ] T034 [US3] Integrate startup readiness bootstrap execution into CLI startup and service initialization flow in /home/xavier/PycharmProjects/AnonymApp/src/app/cli/main.py and /home/xavier/PycharmProjects/AnonymApp/src/services/readiness_service.py
- [ ] T035 [US3] Implement optional service availability checks (e.g., Ollama non-blocking probe) in /home/xavier/PycharmProjects/AnonymApp/src/bootstrap/dependency_check.py and /home/xavier/PycharmProjects/AnonymApp/src/bootstrap/readiness_bootstrap.py
- [ ] T036 [US3] Add unit tests for bootstrap dependency/model checks and readiness status transitions in /home/xavier/PycharmProjects/AnonymApp/tests/unit/bootstrap/test_readiness_bootstrap.py
- [ ] T037 [US3] Add integration tests for missing dependency/model readiness failure behavior with actionable messages in /home/xavier/PycharmProjects/AnonymApp/tests/integration/test_readiness_failures.py

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
- Do not modify `tmp/anonymizer.py` or `tmp/transformer_anonymizer.py`.

### Séquençage (sans parallélisme)

- Exécuter les tâches strictement dans l’ordre numérique `T001 -> T037`.
- Ne démarrer aucune tâche suivante tant que la tâche courante n’est pas validée.
- Conserver les checkpoints de phase comme points de validation obligatoires.

---

## Implementation Strategy

### MVP First (Minimum Deliverable)

1. Complete Phase 0 and Phase 1.
2. Complete Phase 2 (Backend A anonymization/export).
3. Validate with T024.
4. Stop for MVP review before enabling full backend switching/deanonymization.

### Incremental Delivery

1. Add Backend B parity (Phase 3).
2. Add deanonymization and compatibility (Phase 4).
3. Add readiness hardening for non-technical Windows users (Phase 5).

### Constraints Enforcement

- No cloud dependencies.
- No complex GUI framework in MVP.
- No distributed architecture.
- No cross-platform packaging work in this task set.
