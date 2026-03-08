# Feature Specification: Windows Desktop Anonymization MVP

**Feature Branch**: `001-build-desktop-anonymizer`  
**Created**: 2026-03-07  
**Status**: Draft  
**Input**: User description: "Standalone desktop anonymization application that wraps two existing Python anonymization backends, runs locally, and supports anonymization/deanonymization workflows with mapping export/import."

## Constitution Alignment *(mandatory)*

- **Engine Reuse Impact**: The feature reuses `./tmp/transformer_anonymizer.py` and `./tmp/anonymizer.py` as source-of-truth anonymization engines. The MVP adds wrappers/adapters only and avoids changing internal anonymization behavior.
  Integration occurs through thin wrappers that adapt input/output and preserve
  source-script behavior.
- **Layer Boundaries**: The feature defines explicit UI, application/service, engine abstraction, document adapter, and configuration/storage layers. User-facing workflows interact only through the application layer and canonical result structures.
- **Local-First Guarantee**: Core anonymization and deanonymization workflows run entirely on local files and local runtime components. Optional external services, if configured, never block core flows.
- **Determinism & Auditability**: The feature standardizes anonymization results into a canonical structure with anonymized text, mapping artifacts, and run metadata so outputs are reproducible and auditable.
- **Extensibility Impact**: Engine wrappers and document adapters are defined as interchangeable components, allowing additional engines and formats to be added without changing UI workflows.
- **Windows Desktop Usability**: The MVP targets non-technical Windows users and prepares for self-contained desktop packaging so users do not depend on manual Python or command-line setup.
- **CPU-Only Execution**: The MVP intentionally targets CPU-only execution to
  maximize compatibility on standard Windows desktops; GPU acceleration is not a
  requirement for functional behavior.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Anonymize TXT with Selected Backend (Priority: P1)

A user selects a local TXT file, chooses one of the two available anonymization backends, runs anonymization, and previews the anonymized result before exporting artifacts.

**Why this priority**: This is the core value of the product and the minimum deliverable for the standalone MVP.

**Independent Test**: A user can complete file selection, backend selection, anonymization, preview, and export of anonymized output and mapping artifacts in one session.

**Acceptance Scenarios**:

1. **Given** a valid local TXT file and backend A selected, **When** the user runs anonymization, **Then** the application shows anonymized text in the preview and enables export of anonymized text and mapping data.
2. **Given** a valid local TXT file and backend B selected, **When** the user runs anonymization, **Then** the application shows anonymized text in the same UI workflow and enables export of anonymized text and mapping data.
3. **Given** an anonymization result from either backend, **When** the user exports artifacts, **Then** exported outputs contain anonymized text and mapping data consistent with the shown preview.
4. **Given** a packaged Windows release of the application, **When** a
   non-technical user starts anonymization, **Then** no command-line interaction
   or manual dependency setup is required.

---

### User Story 2 - Deanonymize with Mapping Data (Priority: P2)

A user loads previously anonymized text and mapping data, then restores original content through a deanonymization workflow.

**Why this priority**: Deanonymization is required for operational use of mappings and validates that mapping artifacts are usable, not just stored.

**Independent Test**: A user can import valid mapping data and produce deanonymized text that matches the original text associated with that mapping.

**Acceptance Scenarios**:

1. **Given** a previously anonymized TXT file and its compatible mapping file, **When** the user runs deanonymization, **Then** the application restores original text and allows export.
2. **Given** an incompatible or corrupted mapping file, **When** the user attempts deanonymization, **Then** the application displays a clear error and does not produce invalid output.

---

### User Story 3 - Reliable Backend Switching and Error Recovery (Priority: P3)

A user switches between backends without changing the UI workflow and receives actionable error feedback when dependencies or backend initialization fail.

**Why this priority**: Backend interchangeability and graceful failure handling are required to make the MVP usable on standard Windows desktops.

**Independent Test**: A user can switch backends in the same UI flow and still complete anonymization when available; if a backend fails to initialize, the user can recover by choosing another backend or fixing configuration.

**Acceptance Scenarios**:

1. **Given** both backends are available, **When** the user switches from backend A to backend B, **Then** the same anonymization workflow remains unchanged and produces a normalized result for each backend.
2. **Given** a backend cannot initialize due to missing local dependencies, **When** the user selects that backend, **Then** the application provides actionable recovery guidance and allows selecting another backend.
3. **Given** an optional service is unavailable, **When** anonymization is run, **Then** the application completes core local anonymization or reports a non-blocking warning without crashing.
4. **Given** first launch on a Windows desktop, **When** required backend dependencies are missing, **Then** the application shows a readiness report with clear recovery actions and prevents invalid backend execution.

### Edge Cases

- Selected input file is empty, unreadable, or not valid plain text.
- Input contains entity patterns unsupported by one backend but supported by the other.
- Mapping export path is not writable.
- Mapping import file exists but has invalid schema or missing required fields.
- Backend runtime dependencies are partially installed on Windows.
- Backend initialization times out or fails during startup.
- Optional services are unavailable while local processing remains available.
- File paths include Windows-specific separators, spaces, or non-ASCII file names.
- A mapping generated by one backend is loaded while only the other backend is available.
- Startup readiness checks detect partially available dependencies (runtime available but model assets missing).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a desktop-oriented local workflow to select a TXT file, select a backend, run anonymization, preview anonymized output, and export artifacts.
- **FR-002**: System MUST reuse the two existing anonymization scripts in `./tmp` as the source of truth for anonymization behavior.
- **FR-003**: System MUST integrate existing scripts through wrappers/adapters and MUST NOT rewrite their internal anonymization logic.
- **FR-004**: System MUST define and use a common engine interface so UI and higher layers remain backend-agnostic.
- **FR-005**: System MUST normalize outputs from both backends into a canonical anonymization result structure containing anonymized text, mapping data, replacement/entity metadata, and optional pseudonymization metadata.
- **FR-006**: System MUST support exporting anonymized text output and mapping data as local files.
- **FR-007**: System MUST support loading mapping data and performing deanonymization on previously anonymized text.
- **FR-008**: System MUST detect and report incompatible mapping files with actionable user guidance.
- **FR-009**: System MUST define an application environment setup artifact that lists required backend dependencies and establishes a reproducible local runtime environment for end users.
- **FR-010**: System MUST define dependency management artifacts for the runtime environment so the anonymization engines can be imported and executed as application modules.
- **FR-011**: System MUST run the core anonymization/deanonymization workflow locally without requiring cloud APIs.
- **FR-012**: System MUST treat optional external services as non-mandatory and preserve core workflow availability when those services are unavailable.
- **FR-013**: System MUST enforce layered boundaries across UI, application/service, engine abstraction, document adapter, and configuration/storage responsibilities.
- **FR-014**: System MUST provide TXT document loading/saving for MVP and MUST define extension points for future PDF, DOCX, and XLSX adapters.
- **FR-015**: System MUST store local configuration, model/backend settings, logs, and mapping artifacts in a Windows-compatible manner.
- **FR-016**: System MUST support native execution on standard Windows desktops without requiring Linux runtime environments.
- **FR-017**: System MUST keep file handling, path handling, and process invocation compatible with Windows conventions.
- **FR-018**: System MUST avoid Linux-only operational assumptions in user-facing workflows and runtime behavior.
- **FR-019**: System MUST allow backend switching within the same UI flow without requiring workflow changes from the user.
- **FR-020**: System MUST preserve future option for cross-platform support without making it an MVP requirement.
- **FR-021**: For the packaged Windows release target, system MUST provide an
  end-user workflow that does not require users to install Python, manage
  dependencies manually, or run command-line tools; a thin CLI interface is
  acceptable for MVP/internal delivery as an intermediate step.
- **FR-022**: System MUST define packaging requirements for a self-contained Windows desktop distribution suitable for non-technical users.
- **FR-023**: As the implementation rule for FR-003, system MUST integrate
  `./tmp/anonymizer.py` and `./tmp/transformer_anonymizer.py` through thin
  wrapper modules that only adapt inputs, invoke the backend, normalize outputs,
  and handle configuration/error translation.
- **FR-024**: As a guardrail for FR-002/FR-003, thin wrappers MUST NOT
  duplicate, reimplement, or alter core anonymization logic contained in the
  source scripts.
- **FR-025**: As the implementation rule for FR-005, system MUST define one
  canonical anonymization result object used by UI and higher layers for all
  backend outputs.
- **FR-026**: The canonical anonymization result object MUST include, at minimum: `anonymized_text`, `mapping`, `entities`, `engine_id`, `processing_metadata`, and optional `pseudonym_metadata`.
- **FR-027**: Backend-specific output formats MUST be converted into the canonical anonymization result before being returned to application/service or UI layers.
- **FR-028**: Exported mapping artifacts for MVP MUST use a canonical mapping format; backend-native mapping export is out of scope unless explicitly added in a future feature.
- **FR-029**: Canonical mapping artifacts MUST include metadata required for
  compatibility verification: `origin.engine_id`, `schema_version`,
  `origin.generated_at`, `origin.wrapper_contract_version`, and
  `mapping_format`.
- **FR-030**: System MUST validate mapping compatibility before deanonymization and MUST route deanonymization through the backend wrapper matching the mapping's origin metadata.
- **FR-031**: If the required backend for mapping-based deanonymization is unavailable, the system MUST block execution and provide actionable recovery guidance.
- **FR-032**: System MUST define a backend readiness workflow that verifies runtime dependencies and required model assets for each backend at startup and on first launch.
- **FR-033**: System MUST provide user-facing readiness status per backend
  (`ready`, `degraded`, `unavailable`) with remediation guidance suitable for
  non-technical Windows users, with minimum state criteria:
  `ready` = all required runtime and model checks pass;
  `degraded` = core local anonymization is available but at least one optional
  capability/check fails;
  `unavailable` = one or more required runtime/model checks fail, so backend
  execution is blocked.
- **FR-034**: System MUST define Windows runtime bootstrap behavior so end users can launch and use the app without manual Python environment creation.
- **FR-035**: On first launch, system MUST execute dependency validation and present a clear status summary before anonymization can start.
- **FR-036**: System MUST run all anonymization and deanonymization workflows in
  CPU-only mode.
- **FR-037**: System MUST NOT require or assume CUDA, MPS, or any GPU runtime to
  function.
- **FR-038**: Backend initialization MUST force Hugging Face pipelines to
  `device=-1` and MUST load Torch-based models on CPU.
- **FR-039**: System MUST explicitly disable GPU device selection in application
  runtime behavior, even when CUDA libraries are present.

### Key Entities *(include if feature involves data)*

- **Anonymization Job**: A user-requested operation containing selected input file, selected backend, options, execution status, timestamps, and output references.
- **Backend Descriptor**: Metadata describing each available engine, availability state, initialization status, and capability flags exposed to the UI.
- **Canonical Anonymization Result**: Normalized output object with required fields:
  `anonymized_text`, `mapping`, `entities`, `engine_id`, `processing_metadata`,
  and optional `pseudonym_metadata`.
- **Mapping Artifact**: Canonical persisted mapping dataset used for export,
  audit, and deanonymization workflows; includes compatibility metadata:
  `origin.engine_id`, `schema_version`, `origin.generated_at`,
  `origin.wrapper_contract_version`, and `mapping_format`.
- **Document Asset**: Input/output file representation including file type, path, validation state, and encoding metadata.
- **Application Configuration**: Local settings for backend preferences, runtime behavior, output locations, and logging controls.

## Assumptions

- MVP users are single-user desktop operators processing local text files.
- Authentication and multi-user access controls are out of scope for MVP.
- The two existing backend scripts are functionally valid and remain the behavioral reference.
- Backend-specific output differences can be normalized into one canonical internal result without changing core engine logic.
- Windows is the primary user platform; Linux/WSL may be used for development but not required for end-user runtime.
- The `<10s` runtime target for typical TXT files under 1 MB is a non-binding
  MVP planning assumption (guidance target), not a release-gate requirement in
  this specification.

## Dependencies

- Availability of the two existing anonymization scripts under `./tmp`.
- Availability of required local runtime dependencies for each backend on Windows desktops.
- Local filesystem access for reading TXT files and writing output/mapping/log artifacts.
- Availability of backend model assets required for each anonymization engine.
- CPU execution environment availability is sufficient; GPU libraries are
  optional and must not be required.

## Mapping Compatibility Rules

- MVP exports mapping artifacts in canonical format only.
- Each mapping file MUST include `origin.engine_id`, `schema_version`,
  `origin.generated_at`, `origin.wrapper_contract_version`, and
  `mapping_format`.
- Deanonymization MUST validate mapping schema/version and origin metadata before
  execution.
- Deanonymization MUST use the backend wrapper identified by mapping origin
  metadata.
- If mapping compatibility validation fails, the system MUST return a
  user-actionable error and MUST NOT emit deanonymized output.

## Windows Runtime Bootstrap Expectations

- The application distribution MUST include or provision required runtime
  components so end users do not manually install or configure Python.
- On first launch, the app MUST run backend readiness validation and display
  per-backend status and remediation guidance.
- On every launch, the app MUST check backend initialization readiness before the
  user starts anonymization.
- Backend readiness state semantics MUST be consistent with FR-033:
  `ready` (all required checks pass),
  `degraded` (required checks pass, optional checks fail),
  `unavailable` (one or more required checks fail).
- If dependencies or model assets are missing, the app MUST provide clear
  recovery guidance in plain language and keep unaffected backends available.
- Runtime readiness checks MUST validate CPU-only backend configuration and MUST
  not require CUDA/MPS availability.
- If CUDA libraries are present, application behavior MUST remain CPU-only and
  deterministic.

## Backend Initialization Guidelines

- Both backends MUST be initialized in CPU mode.
- Hugging Face pipelines MUST use `device=-1`.
- Torch model loading MUST target CPU and MUST NOT rely on `cuda` or `mps`
  availability.
- Backend wrappers/bootstrap logic MUST disable or ignore GPU device-selection
  hints from runtime defaults.
- CPU-only execution is intentional to ensure compatibility with standard
  Windows desktops used by non-technical users.

## Non-Goals

- Rewriting anonymization algorithms in existing backends.
- Replacing GLiNER, existing NER models, or creating new anonymization models.
- Requiring cloud inference or external cloud APIs for core functionality.
- Delivering full PDF, DOCX, and XLSX document processing in the MVP.
- Making Linux or macOS parity a release requirement for the MVP.
- Requiring end users to perform manual Python runtime installation or command-line-based setup.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 95% of test users can complete TXT anonymization (select file, choose backend, run, preview, export) without assistance in under 3 minutes.
- **SC-002**: For both backends, 100% of MVP acceptance test scenarios for anonymization, mapping export, and backend switching pass.
- **SC-003**: At least 95% of valid mapping import attempts successfully deanonymize corresponding anonymized text in acceptance testing.
- **SC-004**: 100% of defined error scenarios (missing dependency, backend initialization failure, optional service unavailable, incompatible mapping file) return actionable user-facing feedback with no application crash.
- **SC-005**: In UAT on standard Windows desktops, core anonymization workflows execute without requiring Linux-specific shell commands or Linux runtime components.
- **SC-006**: In UAT, at least 90% of non-technical users can install and launch the application on Windows without manual Python setup or command-line actions.
