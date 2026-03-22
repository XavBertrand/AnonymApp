# Tasks: A4 Desktop Case Workspace

**Input**: Design documents from `/specs/002-desktop-case-ui/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are required by the feature spec and are included in each relevant phase.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing. Within each phase, tasks are grouped by layer in this order: persistence, service/application, UI (desktop), packaging, tests.

**Constitution Compliance**: These tasks are aligned with the project constitution. UI remains thin and event-driven, business logic stays in the service layer, persistence adapters remain data-focused, CLI behavior must remain unchanged, and TXT-only MVP remains in force.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (e.g. `US1`, `US2`)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/`, `scripts/` at repository root
- Desktop UI: `src/app/desktop/`
- Service/application orchestration: `src/services/`
- Persistence adapters: `src/adapters/persistence/`
- Document adapter seam: `src/adapters/documents/`
- UI DTO/view models: `src/app/ui_contracts/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add desktop, persistence, document-adapter, packaging, and test scaffolding without changing current CLI behavior.

- [X] T001 Add desktop and packaging dependencies to `pyproject.toml`
- [X] T002 Create package skeleton files in `src/app/desktop/__init__.py`, `src/app/desktop/widgets/__init__.py`, `src/app/desktop/presenters/__init__.py`, `src/app/desktop/workers/__init__.py`, `src/app/desktop/copy/__init__.py`, `src/adapters/documents/__init__.py`, `src/adapters/persistence/__init__.py`, `tests/ui/__init__.py`, `tests/packaging/__init__.py`, and `tests/unit/adapters/documents/__init__.py`
- [X] T003 [P] Add desktop-specific path and storage constants in `src/config/desktop_settings.py`
- [X] T004 [P] Define UI-facing DTO/view model module in `src/app/ui_contracts/case_workspace_view_models.py`
- [X] T005 [P] Create portable packaging script stubs in `scripts/packaging/build_windows_portable.py` and `scripts/packaging/smoke_test_portable.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the blocking foundation for persistence, orchestration, deterministic mapping, document-adapter wiring, background execution, and CLI-safe integration.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Persistence

- [X] T006 Create metadata database bootstrap and schema management in `src/adapters/persistence/database.py`
- [X] T007 [P] Define persistence record types in `src/adapters/persistence/records.py`
- [X] T008 [P] Create thin case repository interface and storage adapter in `src/adapters/persistence/case_repository.py`
- [X] T009 [P] Create thin document repository interface and storage adapter in `src/adapters/persistence/document_repository.py`
- [X] T010 [P] Create thin mapping revision repository interface and storage adapter in `src/adapters/persistence/mapping_revision_repository.py`
- [X] T011 [P] Create thin job repository interface and storage adapter in `src/adapters/persistence/job_repository.py`
- [X] T012 [P] Create thin artifact repository interface and storage adapter in `src/adapters/persistence/artifact_repository.py`
- [X] T013 [P] Create thin deanonymization session repository interface and storage adapter in `src/adapters/persistence/deanonymization_session_repository.py`
- [X] T014 [P] Create thin review decision repository interface and storage adapter in `src/adapters/persistence/review_decision_repository.py`
- [X] T015 [P] Create file-based artifact store adapter in `src/adapters/persistence/artifact_store.py`

### Service/Application

- [X] T016 Create the document-adapter contract and registry seam in `src/adapters/documents/contract.py` and `src/adapters/documents/registry.py`
- [X] T017 Create the TXT document adapter and register it through CaseWorkspaceService wiring in `src/adapters/documents/txt_adapter.py` and `src/services/case_workspace_service.py`
- [X] T018 Create service-layer mapping revision policy in `src/services/mapping_revision_service.py`
- [X] T019 Create deterministic conflict resolution policy with earliest-wins behavior in `src/services/case_mapping_policy.py`
- [X] T020 Create stale-state propagation service in `src/services/stale_state_service.py`
- [X] T021 Create CaseWorkspaceService skeleton and dependency wiring in `src/services/case_workspace_service.py`
- [X] T022 Enforce that MappingRevision is the single source of truth for case mapping state in `src/services/case_workspace_service.py` and `src/services/mapping_revision_service.py`
- [X] T023 Centralize CLI-safe shared orchestration helpers in `src/services/case_workspace_service.py` without changing `src/app/cli/main.py`, `src/services/anonymization_service.py`, or `src/services/deanonymization_service.py`

### UI (Desktop)

- [X] T024 Create desktop application bootstrap in `src/app/desktop/main.py`
- [X] T025 Create thin main window shell in `src/app/desktop/window.py`
- [X] T026 Create workspace presenter that talks only to CaseWorkspaceService in `src/app/desktop/presenters/workspace_presenter.py`
- [X] T027 Create background worker runner so long-running jobs stay off the UI thread in `src/app/desktop/workers/workspace_worker.py`

### Packaging

- [X] T028 Create PyInstaller entry configuration stub in `scripts/packaging/a4_desktop.spec`

### Tests

- [X] T029 [P] Add unit tests proving the document-adapter seam exists and TXT uses it in `tests/unit/adapters/documents/test_txt_document_adapter.py`
- [X] T030 [P] Add integration tests proving desktop orchestration reuses service APIs directly without CLI shell-out in `tests/integration/test_desktop_service_reuse.py`
- [X] T031 [P] Add unit tests for deterministic mapping policy across repeated runs in `tests/unit/services/test_case_mapping_policy.py`
- [X] T032 [P] Add unit tests that assert persistence adapters stay data-focused in `tests/unit/persistence/test_repository_boundaries.py`
- [X] T033 Add CLI regression safety baseline in `tests/integration/test_cli_desktop_regression.py`

**Checkpoint**: Foundation ready. The UI can only call CaseWorkspaceService; TXT flows through the document-adapter seam; mapping logic is centralized in the service layer; persistence adapters are thin; background job execution is available.

---

## Phase 3: User Story 1 - Create a case and anonymize files (Priority: P1) 🎯 MVP

**Goal**: Let a user create or open a case and anonymize one or more TXT files inside that case with a shared deterministic mapping.

**Independent Test**: Create a case, select one or more TXT files, run anonymization, confirm sequential progress, saved outputs, per-file statuses, and stable shared mapping without using the CLI.

### Persistence

- [X] T034 [US1] Implement case create/list/load methods in `src/adapters/persistence/case_repository.py`
- [X] T035 [P] [US1] Implement document import and status persistence in `src/adapters/persistence/document_repository.py`
- [X] T036 [P] [US1] Implement job lifecycle persistence for batch anonymization in `src/adapters/persistence/job_repository.py`
- [X] T037 [P] [US1] Implement artifact creation and lookup persistence in `src/adapters/persistence/artifact_repository.py`
- [X] T038 [P] [US1] Implement case working-file storage and exported artifact naming in `src/adapters/persistence/artifact_store.py`

### Service/Application

- [X] T039 [US1] Implement `create_case`, `load_workspace`, and `open_case` orchestration in `src/services/case_workspace_service.py`
- [X] T040 [US1] Implement multi-file batch anonymization orchestration with sequential execution in `src/services/case_workspace_service.py`
- [X] T041 [US1] Implement deterministic batch mapping merge using MappingRevision in `src/services/mapping_revision_service.py`
- [X] T042 [US1] Apply earliest-wins conflict resolution during shared case mapping merge in `src/services/case_mapping_policy.py`
- [X] T043 [US1] Persist batch outputs and mapping-revision links through CaseWorkspaceService in `src/services/case_workspace_service.py`
- [X] T044 [US1] Map service results into UI view models only in `src/services/case_workspace_service.py` and `src/app/ui_contracts/case_workspace_view_models.py`

### UI (Desktop)

- [X] T045 [US1] Build the left-side case list and create-case action in `src/app/desktop/widgets/case_history_panel.py`
- [X] T046 [P] [US1] Build the central file selection and batch-run controls in `src/app/desktop/widgets/case_workspace_panel.py`
- [X] T047 [P] [US1] Build the anonymization result preview panel in `src/app/desktop/widgets/result_preview_panel.py`
- [X] T048 [US1] Wire create/open/anonymize actions through the presenter and worker only in `src/app/desktop/presenters/workspace_presenter.py` and `src/app/desktop/workers/workspace_worker.py`
- [X] T049 [US1] Add per-file progress and batch status updates in `src/app/desktop/window.py` and `src/app/desktop/widgets/case_workspace_panel.py`

### Packaging

- [X] T050 [US1] Ensure development desktop entry point resolves packaged assets safely in `scripts/packaging/build_windows_portable.py` and `src/app/desktop/main.py`

### Tests

- [X] T051 [P] [US1] Add unit tests for case creation and batch orchestration in `tests/unit/services/test_case_workspace_service_batch.py`
- [X] T052 [P] [US1] Add integration tests for shared mapping across multiple TXT files in `tests/integration/test_case_batch_shared_mapping.py`
- [X] T053 [P] [US1] Add integration tests for deterministic conflict resolution across multiple files in `tests/integration/test_case_mapping_conflicts.py`
- [X] T054 [P] [US1] Add UI tests for create-case and file anonymization flow in `tests/ui/test_case_creation_and_batch.py`
- [X] T055 [US1] Add integration test for partial batch failure continuation in `tests/integration/test_case_batch_partial_failure.py`

**Checkpoint**: User Story 1 is independently functional and testable as the MVP.

---

## Phase 4: User Story 2 - Reopen and inspect a case (Priority: P1)

**Goal**: Let a user reopen an existing case from history and inspect files, outputs, statuses, snippets, current/stale state, and case deletion behavior.

**Independent Test**: Create and process a case, restart the app, reopen the case from history, inspect saved documents, artifacts, statuses, snippets, and missing/stale indicators, then delete the case through a confirmation flow.

### Persistence

- [ ] T056 [US2] Implement last-opened and case-history ordering queries in `src/adapters/persistence/case_repository.py`
- [ ] T057 [P] [US2] Implement artifact freshness and missing-file lookup queries in `src/adapters/persistence/artifact_repository.py`
- [ ] T058 [P] [US2] Persist preview snippets and source fingerprints in `src/adapters/persistence/document_repository.py`
- [ ] T059 [US2] Implement internal soft-delete persistence with no user-facing recovery flow in MVP in `src/adapters/persistence/case_repository.py`

### Service/Application

- [ ] T060 [US2] Implement case history and reopened-workspace aggregation in `src/services/case_workspace_service.py`
- [ ] T061 [US2] Implement case-level status summary derivation in `src/services/case_workspace_service.py`
- [ ] T062 [US2] Surface missing-artifact and stale-artifact states through view models in `src/services/case_workspace_service.py` and `src/app/ui_contracts/case_workspace_view_models.py`
- [ ] T063 [US2] Implement `delete_case` orchestration and post-delete history refresh in `src/services/case_workspace_service.py`

### UI (Desktop)

- [ ] T064 [US2] Build persistent case history panel behavior in `src/app/desktop/widgets/case_history_panel.py`
- [ ] T065 [P] [US2] Build case file/output inspection tables in `src/app/desktop/widgets/case_workspace_panel.py`
- [ ] T066 [P] [US2] Show snippets, statuses, and stale/missing badges in `src/app/desktop/widgets/result_preview_panel.py`
- [ ] T067 [US2] Build delete confirmation UI in `src/app/desktop/widgets/delete_case_dialog.py`
- [ ] T068 [US2] Wire reopen-case and delete-case flows through the presenter in `src/app/desktop/presenters/workspace_presenter.py` and `src/app/desktop/window.py`

### Packaging

- [ ] T069 [US2] Validate user-facing export location resolution for reopened cases in `scripts/packaging/build_windows_portable.py` and `src/config/desktop_settings.py`

### Tests

- [ ] T070 [P] [US2] Add persistence integrity tests for case reopen and artifact references in `tests/unit/persistence/test_case_reopen_integrity.py`
- [ ] T071 [P] [US2] Add integration tests for reopen-after-restart behavior in `tests/integration/test_case_reopen_history.py`
- [ ] T072 [P] [US2] Add UI tests for reopening a case from history in `tests/ui/test_case_history_reopen.py`
- [ ] T073 [P] [US2] Add UI and integration tests for delete confirmation and post-delete behavior in `tests/ui/test_case_delete_flow.py` and `tests/integration/test_case_delete_behavior.py`

**Checkpoint**: User Stories 1 and 2 are independently testable, and case history continuity and deletion are working.

---

## Phase 5: User Story 3 - Review and remove substitutions (Priority: P2)

**Goal**: Let a user review substitutions, remove unwanted ones, regenerate the preview, explicitly regenerate stale outputs when allowed, and mark all impacted prior outputs stale using MappingRevision as the source of truth.

**Independent Test**: Process a case, open substitution review for a file, remove a substitution, confirm a new mapping revision is created, the preview regenerates, impacted older outputs are marked stale deterministically, and stale outputs can only be regenerated through an explicit eligible action.

### Persistence

- [ ] T074 [US3] Implement review decision persistence in `src/adapters/persistence/review_decision_repository.py`
- [ ] T075 [P] [US3] Implement mapping revision write/read methods for review changes in `src/adapters/persistence/mapping_revision_repository.py`
- [ ] T076 [P] [US3] Implement impacted-artifact linkage queries in `src/adapters/persistence/artifact_repository.py`

### Service/Application

- [ ] T077 [US3] Implement substitution review loading in `src/services/case_workspace_service.py`
- [ ] T078 [US3] Implement substitution removal workflow in `src/services/case_workspace_service.py`
- [ ] T079 [US3] Implement mapping revision creation for removals in `src/services/mapping_revision_service.py`
- [ ] T080 [US3] Implement deterministic stale-state propagation after mapping changes in `src/services/stale_state_service.py`
- [ ] T081 [US3] Implement explicit user-triggered stale-output regeneration workflow in `src/services/case_workspace_service.py`
- [ ] T082 [US3] Implement reopened-review editability eligibility checks in `src/services/case_workspace_service.py`
- [ ] T083 [US3] Regenerate current preview from the new MappingRevision in `src/services/case_workspace_service.py`
- [ ] T084 [US3] Ensure no transient or UI-local mapping state can diverge from MappingRevision in `src/services/case_workspace_service.py` and `src/app/ui_contracts/case_workspace_view_models.py`

### UI (Desktop)

- [ ] T085 [US3] Build substitution review panel UI in `src/app/desktop/widgets/mapping_review_panel.py`
- [ ] T086 [P] [US3] Add impacted-output details view and stale indicators in `src/app/desktop/widgets/result_preview_panel.py`
- [ ] T087 [US3] Add explicit stale-output regeneration action with eligibility state in `src/app/desktop/widgets/result_preview_panel.py`
- [ ] T088 [US3] Wire review, removal, and regeneration actions through the presenter only in `src/app/desktop/presenters/workspace_presenter.py`

### Packaging

- [ ] T089 [US3] Validate regenerated artifact naming and supersession behavior in `scripts/packaging/smoke_test_portable.py`

### Tests

- [ ] T090 [P] [US3] Add unit tests for mapping revision increments and earliest-wins conflict behavior in `tests/unit/services/test_mapping_revision_service.py`
- [ ] T091 [P] [US3] Add unit tests for stale-state propagation correctness in `tests/unit/services/test_stale_state_service.py`
- [ ] T092 [P] [US3] Add integration tests for substitution removal and regeneration in `tests/integration/test_case_review_regeneration.py`
- [ ] T093 [P] [US3] Add integration tests for stale impacted outputs after removal in `tests/integration/test_case_stale_outputs.py`
- [ ] T094 [P] [US3] Add integration tests for explicit stale-output regeneration flow in `tests/integration/test_case_stale_regeneration.py`
- [ ] T095 [P] [US3] Add integration tests for unsafe reopen and editability gating in `tests/integration/test_case_review_editability.py`
- [ ] T096 [P] [US3] Add UI tests for mapping review, removal, and regeneration flow in `tests/ui/test_mapping_review_panel.py`

**Checkpoint**: User Story 3 is independently functional with deterministic mapping revisioning, explicit regeneration, and safe editability gating.

---

## Phase 6: User Story 4 - Deanonymize newly pasted anonymized text (Priority: P2)

**Goal**: Let a user paste anonymized text into an existing case, deanonymize it using the current MappingRevision, view the result in-app, and export it.

**Independent Test**: Open an existing case, paste anonymized text, run deanonymization off the UI thread, verify matched and zero-match outcomes, and export the result.

### Persistence

- [ ] T097 [US4] Implement deanonymization session persistence in `src/adapters/persistence/deanonymization_session_repository.py`
- [ ] T098 [P] [US4] Implement export artifact persistence for pasted deanonymization in `src/adapters/persistence/artifact_repository.py`

### Service/Application

- [ ] T099 [US4] Implement pasted deanonymization orchestration in `src/services/case_workspace_service.py`
- [ ] T100 [US4] Resolve pasted deanonymization strictly from the active MappingRevision in `src/services/case_workspace_service.py`
- [ ] T101 [US4] Implement zero-match and partial-match result handling in `src/services/case_workspace_service.py`
- [ ] T102 [US4] Implement deanonymized export workflow in `src/services/case_workspace_service.py`

### UI (Desktop)

- [ ] T103 [US4] Build pasted-text deanonymization input/output panel in `src/app/desktop/widgets/deanonymization_panel.py`
- [ ] T104 [P] [US4] Add export action and result-state messaging in `src/app/desktop/widgets/deanonymization_panel.py`
- [ ] T105 [US4] Wire pasted deanonymization through the presenter and background worker in `src/app/desktop/presenters/workspace_presenter.py` and `src/app/desktop/workers/workspace_worker.py`

### Packaging

- [ ] T106 [US4] Validate exported deanonymized file paths in portable mode in `scripts/packaging/smoke_test_portable.py`

### Tests

- [ ] T107 [P] [US4] Add unit tests for deanonymization session handling in `tests/unit/services/test_case_workspace_service_deanonymization.py`
- [ ] T108 [P] [US4] Add integration tests for pasted deanonymization with known and unknown matches in `tests/integration/test_pasted_deanonymization.py`
- [ ] T109 [P] [US4] Add integration tests for zero-match unchanged output in `tests/integration/test_pasted_deanonymization_zero_match.py`
- [ ] T110 [P] [US4] Add cross-story round-trip anonymize/deanonymize coherence tests in `tests/integration/test_case_round_trip_coherence.py`
- [ ] T111 [P] [US4] Add UI tests for pasted deanonymization flow in `tests/ui/test_deanonymization_panel.py`

**Checkpoint**: User Story 4 is independently functional and uses the current case mapping without UI-side business logic.

---

## Phase 7: User Story 5 - Monitor readiness without technical noise (Priority: P3)

**Goal**: Surface a simple readiness indicator with optional detail while keeping the workspace understandable for non-technical users.

**Independent Test**: Launch the app with ready and blocked model states and confirm the main window shows a discreet summary, a details mode, and correct action blocking.

### Persistence

- [ ] T112 [US5] Persist optional readiness snapshots for case/job inspection in `src/adapters/persistence/job_repository.py`

### Service/Application

- [ ] T113 [US5] Implement readiness summary and detail DTO generation in `src/services/case_workspace_service.py`
- [ ] T114 [US5] Implement blocked-action guardrails for anonymization and deanonymization in `src/services/case_workspace_service.py`

### UI (Desktop)

- [ ] T115 [US5] Build discreet readiness summary widget in `src/app/desktop/widgets/readiness_panel.py`
- [ ] T116 [P] [US5] Build readiness details dialog in `src/app/desktop/widgets/readiness_details_dialog.py`
- [ ] T117 [US5] Wire readiness refresh and action blocking through the presenter in `src/app/desktop/presenters/workspace_presenter.py` and `src/app/desktop/window.py`

### Packaging

- [ ] T118 [US5] Verify packaged readiness uses root-relative `models/` resolution in `scripts/packaging/smoke_test_portable.py` and `src/config/desktop_settings.py`

### Tests

- [ ] T119 [P] [US5] Add unit tests for readiness DTO mapping in `tests/unit/services/test_case_workspace_service_readiness.py`
- [ ] T120 [P] [US5] Add UI tests for readiness summary and details mode in `tests/ui/test_readiness_panel.py`
- [ ] T121 [US5] Add packaging-oriented readiness failure test for missing/corrupt models in `tests/packaging/test_portable_readiness_failures.py`

**Checkpoint**: All user stories are independently functional and aligned with the desktop workspace architecture.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Finish packaging, harden UX, verify layering, privacy, localization, and validate the full quickstart.

### Persistence

- [ ] T122 Add missing-artifact reconciliation and cleanup helpers in `src/adapters/persistence/artifact_repository.py` and `src/adapters/persistence/artifact_store.py`

### Service/Application

- [ ] T123 Add cross-cutting error translation for desktop workflows in `src/services/case_workspace_service.py`
- [ ] T124 Add privacy and sensitive-data minimization rules for previews, logs, and persisted metadata in `src/services/privacy_guard.py` and `src/services/case_workspace_service.py`
- [ ] T125 Verify no shared logic was duplicated outside the service layer in `src/services/case_workspace_service.py`, `src/services/mapping_revision_service.py`, `src/services/case_mapping_policy.py`, and `src/services/stale_state_service.py`

### UI (Desktop)

- [ ] T126 Add global and per-file error UX surfaces in `src/app/desktop/widgets/error_banner.py`, `src/app/desktop/widgets/case_workspace_panel.py`, and `src/app/desktop/window.py`
- [ ] T127 Refine dark-theme styling and premium visual polish in `src/app/desktop/styles/dark_theme.qss` and `src/app/desktop/window.py`
- [ ] T128 Add a French UI copy inventory and centralized labels in `src/app/desktop/copy/fr.py`, `src/app/desktop/window.py`, and `src/app/desktop/widgets/`
- [ ] T129 Verify the UI remains thin and event-driven with no mapping or stale-detection business logic in `src/app/desktop/presenters/workspace_presenter.py` and `src/app/desktop/widgets/`

### Packaging

- [ ] T130 Finalize PyInstaller configuration in `scripts/packaging/a4_desktop.spec`
- [ ] T131 Include packaged `models/` assets and icon resources in `scripts/packaging/build_windows_portable.py` and `scripts/packaging/a4_desktop.spec`
- [ ] T132 Validate portable relative path resolution and extracted-folder execution in `scripts/packaging/smoke_test_portable.py`

### Tests

- [ ] T133 [P] Add persistence integrity regression tests in `tests/unit/persistence/test_case_storage_integrity.py`
- [ ] T134 [P] Add sensitive metadata and log-boundary tests in `tests/unit/services/test_privacy_guard.py`
- [ ] T135 [P] Add French UI copy verification tests in `tests/ui/test_french_copy_labels.py`
- [ ] T136 [P] Add end-to-end UI workflow smoke test in `tests/ui/test_desktop_workspace_smoke.py`
- [ ] T137 [P] Add Windows portable packaging smoke test in `tests/packaging/test_windows_portable_smoke.py`
- [ ] T138 Run quickstart validation scenarios in `specs/002-desktop-case-ui/quickstart.md`
- [ ] T139 [P] Add lightweight performance validation for startup, case switching, and first progress update targets in `tests/packaging/test_desktop_performance_smoke.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies; starts immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1; blocks all user stories.
- **Phase 3 (US1)**: Depends on Phase 2; establishes MVP.
- **Phase 4 (US2)**: Depends on Phase 2 and may reuse persisted cases created through US1, but remains independently testable with seeded case fixtures.
- **Phase 5 (US3)**: Depends on Phase 2 and the foundational mapping-revision services; functionally builds on processed-case data from US1.
- **Phase 6 (US4)**: Depends on Phase 2 and active case mapping support from earlier phases.
- **Phase 7 (US5)**: Depends on Phase 2; can be implemented after core workspace shell exists.
- **Phase 8 (Polish)**: Depends on completion of desired user stories.

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Foundational; recommended MVP slice.
- **User Story 2 (P1)**: Starts after Foundational; independently testable with seeded persisted cases.
- **User Story 3 (P2)**: Starts after Foundational; requires mapping-revision and stale-propagation foundation.
- **User Story 4 (P2)**: Starts after Foundational; requires active case mapping and background execution support.
- **User Story 5 (P3)**: Starts after Foundational; depends on the desktop shell and readiness DTOs only.

### Within Each User Story

- Persistence adapter tasks come before service orchestration tasks that rely on them.
- Service/application tasks come before UI wiring.
- Packaging tasks come after the relevant behavior exists.
- Tests validate each story once its layer work is complete.
- No UI task may bypass CaseWorkspaceService or reach persistence, document-adapter state, or mapping state directly.

### Parallel Opportunities

- Repository adapter files in Phase 2 marked `[P]` can be implemented in parallel.
- Document-adapter seam tests and repository-boundary tests can overlap once the foundational interfaces exist.
- DTO, worker, and presenter shell tasks can overlap once the package skeleton exists.
- Within each user story, separate persistence files, widget files, and test files marked `[P]` can run in parallel.
- Packaging smoke work can proceed in parallel with late-stage UI polish once core workflows are stable.

---

## Parallel Example: User Story 1

```bash
# Parallel persistence work
T035 Implement document import and status persistence in src/adapters/persistence/document_repository.py
T036 Implement job lifecycle persistence for batch anonymization in src/adapters/persistence/job_repository.py
T037 Implement artifact creation and lookup persistence in src/adapters/persistence/artifact_repository.py

# Parallel UI work
T046 Build the central file selection and batch-run controls in src/app/desktop/widgets/case_workspace_panel.py
T047 Build the anonymization result preview panel in src/app/desktop/widgets/result_preview_panel.py

# Parallel tests
T051 Add unit tests for case creation and batch orchestration in tests/unit/services/test_case_workspace_service_batch.py
T052 Add integration tests for shared mapping across multiple TXT files in tests/integration/test_case_batch_shared_mapping.py
T054 Add UI tests for create-case and file anonymization flow in tests/ui/test_case_creation_and_batch.py
```

## Parallel Example: User Story 2

```bash
T057 Implement artifact freshness and missing-file lookup queries in src/adapters/persistence/artifact_repository.py
T058 Persist preview snippets and source fingerprints in src/adapters/persistence/document_repository.py
T065 Build case file/output inspection tables in src/app/desktop/widgets/case_workspace_panel.py
T066 Show snippets, statuses, and stale/missing badges in src/app/desktop/widgets/result_preview_panel.py
T070 Add persistence integrity tests for case reopen and artifact references in tests/unit/persistence/test_case_reopen_integrity.py
T073 Add UI and integration tests for delete confirmation and post-delete behavior in tests/ui/test_case_delete_flow.py and tests/integration/test_case_delete_behavior.py
```

## Parallel Example: User Story 3

```bash
T075 Implement mapping revision write/read methods for review changes in src/adapters/persistence/mapping_revision_repository.py
T076 Implement impacted-artifact linkage queries in src/adapters/persistence/artifact_repository.py
T086 Add impacted-output details view and stale indicators in src/app/desktop/widgets/result_preview_panel.py
T090 Add unit tests for mapping revision increments and earliest-wins conflict behavior in tests/unit/services/test_mapping_revision_service.py
T091 Add unit tests for stale-state propagation correctness in tests/unit/services/test_stale_state_service.py
T096 Add UI tests for mapping review, removal, and regeneration flow in tests/ui/test_mapping_review_panel.py
```

## Parallel Example: User Story 4

```bash
T097 Implement deanonymization session persistence in src/adapters/persistence/deanonymization_session_repository.py
T098 Implement export artifact persistence for pasted deanonymization in src/adapters/persistence/artifact_repository.py
T103 Build pasted-text deanonymization input/output panel in src/app/desktop/widgets/deanonymization_panel.py
T104 Add export action and result-state messaging in src/app/desktop/widgets/deanonymization_panel.py
T107 Add unit tests for deanonymization session handling in tests/unit/services/test_case_workspace_service_deanonymization.py
T111 Add UI tests for pasted deanonymization flow in tests/ui/test_deanonymization_panel.py
```

## Parallel Example: User Story 5

```bash
T115 Build discreet readiness summary widget in src/app/desktop/widgets/readiness_panel.py
T116 Build readiness details dialog in src/app/desktop/widgets/readiness_details_dialog.py
T119 Add unit tests for readiness DTO mapping in tests/unit/services/test_case_workspace_service_readiness.py
T120 Add UI tests for readiness summary and details mode in tests/ui/test_readiness_panel.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3: User Story 1.
4. Validate the document-adapter seam, deterministic shared mapping, sequential batch behavior, and partial failure handling.
5. Stop for MVP review before expanding to later stories.

### Incremental Delivery

1. Setup + Foundational establish the only allowed architecture: UI → CaseWorkspaceService → existing services/policies and thin adapters.
2. Deliver User Story 1 as the first usable increment.
3. Deliver User Story 2 for durable case reopening, inspection, and deletion.
4. Deliver User Story 3 for substitution review, revisioning, stale propagation, explicit regeneration, and editability gating.
5. Deliver User Story 4 for pasted deanonymization and round-trip coherence validation using current MappingRevision.
6. Deliver User Story 5 for simplified readiness UX.
7. Finish with packaging, privacy/localization hardening, regression protection, and smoke validation.

### Parallel Team Strategy

1. One developer can own persistence adapters while another builds service orchestration and a third builds thin UI widgets after Phase 2 begins to stabilize.
2. After Foundational completion:
   - Developer A: US1/US2 persistence and service work
   - Developer B: US1/US2 UI work
   - Developer C: test automation, document-adapter seam tests, and packaging scaffolding
3. For US3 and US4, keep all mapping logic inside the service layer and treat UI work as pure event wiring and rendering.

---

## Notes

- All UI workflows MUST go through `CaseWorkspaceService`; no direct UI → service shortcut beyond that entry point is allowed.
- Persistence adapters MUST remain thin and MUST NOT implement mapping logic, conflict resolution, stale detection, or workflow orchestration.
- TXT input MUST flow through the document-adapter seam in `src/adapters/documents/`; future formats can attach there without changing the service-layer workflow.
- Mapping logic MUST remain centralized in the service/application layer and use `MappingRevision` as the single source of truth.
- Long-running anonymization and deanonymization operations MUST run outside the UI thread.
- Existing CLI behavior must remain unchanged throughout implementation.
