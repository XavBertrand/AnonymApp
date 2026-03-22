# Feature Specification: A4 Desktop Case Workspace

**Feature Branch**: `002-desktop-case-ui`  
**Created**: 2026-03-22  
**Status**: Draft  
**Input**: User description: "Windows desktop case-based UI for the existing local anonymization/deanonymization product, preserving current CLI behavior and reusing the current Python service layer directly."

## Constitution Alignment *(mandatory)*

- **Engine Reuse Impact**: The feature reuses the existing anonymization and deanonymization domain behavior as the product authority for text processing. The desktop experience must call the established readiness, anonymization, and deanonymization service entry points directly rather than reproducing or reinterpreting core anonymization logic in the UI layer.
- **Layer Boundaries**: The feature adds a desktop presentation layer, durable case storage, and minimal service-layer extensions for case workflows while preserving the current command-line entry point and existing service behaviors. The UI must not bypass service, wrapper, document adapter, storage, or configuration boundaries.
- **Local-First Guarantee**: All core workflows remain fully local and usable offline. Runtime behavior must not require telemetry, account services, auto-update infrastructure, or model downloads after distribution has been unpacked.
- **Determinism & Auditability**: The product must preserve a durable case record for each legal matter, including file history, operation outcomes, saved outputs, and the active case substitution set used for later deanonymization. Users must be able to understand what was processed, when, and with which resulting substitutions.
- **Extensibility Impact**: TXT remains the only supported document type in MVP, but the specification requires a clean document-type abstraction so that future PDF, DOCX, and XLSX support can be introduced without redesigning the case model or replacing the core case workflows.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a case and anonymize files (Priority: P1)

As a lawyer, I want to create or open a case and anonymize one or more TXT files inside that case so that all files for the same legal matter are processed in one coherent workspace with shared substitutions and automatic saved outputs.

**Why this priority**: This is the primary business workflow and the feature has no value if users cannot process case documents without managing command lines, file paths, or technical settings.

**Independent Test**: Can be fully tested by creating a case, adding multiple TXT files, running anonymization, and confirming that outputs, statuses, and case history are saved without using the CLI.

**Acceptance Scenarios**:

1. **Given** no case is open, **When** the user creates a new case and selects one TXT file to anonymize, **Then** the application saves the case, processes the file locally, and displays the anonymized result with its saved output location and status.
2. **Given** an existing case is open, **When** the user selects multiple TXT files for one anonymization run, **Then** the application processes them sequentially, records a status per file, and keeps successful outputs even if another file fails.
3. **Given** a case already contains prior substitutions, **When** the user anonymizes additional TXT files in the same case, **Then** the run uses the case’s current shared substitution set as the authoritative case mapping for that legal matter.

---

### User Story 2 - Reopen and inspect a case (Priority: P1)

As a lawyer, I want to reopen an existing case from a permanent history panel so that I can continue work later without rebuilding context, re-importing files, or losing outputs and substitution history.

**Why this priority**: Persistent case continuity is central to the product concept and differentiates it from a disposable file conversion tool.

**Independent Test**: Can be fully tested by creating a case, processing files, closing the application, reopening it, selecting the case from history, and verifying that all relevant case data remains available.

**Acceptance Scenarios**:

1. **Given** one or more saved cases exist, **When** the user opens the application, **Then** the left-side history panel lists those cases with enough identifying information to reopen them.
2. **Given** a case has previously processed files and outputs, **When** the user selects that case from history, **Then** the application shows its files, saved outputs, timestamps, statuses, and current substitution state.
3. **Given** the user chooses to delete a case, **When** the deletion is confirmed, **Then** the application removes that case from history and prevents accidental recovery through the normal UI.

---

### User Story 3 - Review and remove substitutions (Priority: P2)

As a lawyer, I want to review substitutions after anonymization and remove substitutions that should not have been applied so that the final anonymized text and future case behavior remain legally usable and coherent.

**Why this priority**: Trust in the substitutions is essential for legal review, and the ability to remove unwanted substitutions is the main corrective workflow requested for MVP.

**Independent Test**: Can be fully tested by anonymizing a TXT file, opening the review table, removing one or more substitutions, regenerating the text, and confirming that the saved case substitution state reflects the removal.

**Acceptance Scenarios**:

1. **Given** a file has been anonymized successfully, **When** the user opens the substitution review table, **Then** the application shows the original and replacement values used for that file in a form suitable for legal review.
2. **Given** a substitution is shown in the review table, **When** the user removes that substitution and confirms regeneration, **Then** the application regenerates the anonymized text without that substitution and updates the case’s active substitution state accordingly.
3. **Given** a removed substitution had been part of the case’s shared mapping, **When** the removal is saved, **Then** future deanonymization and future anonymization behavior for that case must remain internally coherent with the updated case mapping.

---

### User Story 4 - Deanonymize newly pasted anonymized text (Priority: P2)

As a lawyer, I want to paste newly received anonymized text into an existing case and deanonymize it using that case’s mapping so that I can recover readable client content without running a separate pipeline or manually editing placeholders.

**Why this priority**: This is a stated critical business workflow and relies on the case model rather than on a simple file round-trip.

**Independent Test**: Can be fully tested by opening an existing case, pasting anonymized text that contains known case replacements, running deanonymization, reviewing the result, and exporting the restored text.

**Acceptance Scenarios**:

1. **Given** an existing case has a saved active mapping, **When** the user pastes anonymized text into the deanonymization panel, **Then** the application restores all matching replacements that are known to that case and shows the restored text in the same window.
2. **Given** pasted anonymized text contains a mix of known and unknown replacements, **When** the user runs deanonymization, **Then** the application restores the known replacements, leaves unknown content unchanged, and clearly indicates that the output may be partial.
3. **Given** a deanonymized result is shown, **When** the user exports it, **Then** the application saves it with a friendly default filename inside the case’s managed outputs unless the user explicitly chooses another export location.
4. **Given** pasted anonymized text contains no replacements known to the active case mapping, **When** the user runs deanonymization, **Then** the application returns the pasted text unchanged and clearly informs the user that no matches were applied.

---

### User Story 5 - Monitor readiness without technical noise (Priority: P3)

As a lawyer, I want the application to show whether it is ready to process text without forcing me to interpret technical diagnostics unless something is wrong.

**Why this priority**: Readiness matters because the app depends on local models and dependencies, but the primary users are non-technical and should only see details when needed.

**Independent Test**: Can be fully tested by launching the application in ready and not-ready states and verifying that the simplified readiness indicator and optional detail view match the actual processing availability.

**Acceptance Scenarios**:

1. **Given** the application can process text successfully, **When** the main window is shown, **Then** readiness is visible in a discreet simplified form without blocking normal use.
2. **Given** the application is not ready because required local assets are missing, **When** the user opens the application, **Then** the main window shows a clear blocked state with actionable detail available on demand.

### Edge Cases

- What happens when the user creates a case but closes the application before any file is processed?
- How does the system handle a batch where some TXT files are unreadable, empty, duplicated, or already deleted from their original source location?
- How does the feature behave when required local models are missing or fail to initialize at startup or during a run?
- How does the feature behave when a case is reopened after some previously saved output files were manually removed outside the application?
- How does the feature behave when two source files in the same case have the same visible filename but come from different folders?
- How does the feature behave when the user removes a substitution that has already been used in multiple previously saved outputs within the same case?
- How does the feature behave when two files in the same case would otherwise produce different pseudonyms for the same original entity?
- How does the feature behave when pasted deanonymization text contains no known case substitutions?
- How does the feature behave when the persisted case substitution state becomes incompatible with a later bug fix in the anonymization/deanonymization contract?
- How does the feature behave when a case has a large history of processed files and must still remain simple to navigate from one main screen?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a single main-window desktop experience branded as "A4 = Action Avocats Anonym App".
- **FR-002**: The system MUST allow users to create a new case and assign it a human-readable name before or during the first anonymization workflow.
- **FR-003**: The system MUST persist all created cases across application restarts until the user explicitly deletes them.
- **FR-004**: The system MUST provide a permanent left-side history panel listing saved cases and allowing users to reopen them from the main window.
- **FR-005**: The system MUST let the user add one or more TXT files to the currently open case for anonymization.
- **FR-006**: The system MUST process multiple selected TXT files sequentially within one user-triggered run.
- **FR-007**: The system MUST continue processing remaining files in a batch after an individual file fails and MUST record a distinct success or failure status per file.
- **FR-008**: The system MUST save successful anonymized outputs automatically without requiring manual output-path selection in the default flow.
- **FR-009**: The system MUST save mapping and related case artifacts automatically using friendly filenames suitable for non-technical users.
- **FR-010**: The system MUST treat the case, not the individual file, as the authoritative container for shared substitution state, file history, outputs, and deanonymization context.
- **FR-011**: The system MUST maintain a durable active case mapping that can be reused across multiple files processed under the same case.
- **FR-012**: The system MUST enforce deterministic mapping-merge behavior across multiple files processed within the same case.
- **FR-013**: The system MUST ensure that a given original entity resolves to one stable pseudonym within a case unless the user explicitly removes that substitution from the active case mapping.
- **FR-014**: The system MUST NOT silently allow one original entity to remain associated with multiple active pseudonyms inside the same case.
- **FR-015**: The system MUST apply deterministic conflict-resolution rules when identical original entities from different files would otherwise produce different pseudonyms inside the same case, using the earliest mapping established within the case unless an authorized user review action explicitly removes or changes that mapping.
- **FR-016**: The system MUST let the user review substitutions for a processed file as original-to-replacement pairs after anonymization.
- **FR-017**: The system MUST allow users to remove unwanted substitutions from the review table but MUST NOT allow users to add arbitrary new substitutions manually in MVP.
- **FR-018**: The system MUST regenerate the displayed anonymized text after substitution removal so that the preview reflects the updated review state.
- **FR-019**: The system MUST update the persistent case mapping when a substitution removal is confirmed so that later deanonymization remains coherent with the edited case state.
- **FR-020**: The system MUST record a mapping version or equivalent durable change-tracking state for each case mapping update.
- **FR-021**: The system MUST associate each generated output artifact with the mapping version that was active when that artifact was produced.
- **FR-022**: The system MUST retain enough state to determine whether a saved output is current or stale relative to the latest case mapping state.
- **FR-023**: When a substitution is removed from the case mapping, the system MUST mark all affected previously generated outputs as stale rather than silently treating them as current.
- **FR-024**: The system MUST allow the product to require explicit user action before regenerating outputs that became stale because of a case-mapping change.
- **FR-025**: The system MUST clearly indicate which saved outputs are impacted when case-mapping changes make them stale.
- **FR-026**: The system MUST retain enough saved case data to reopen a case later and inspect previous files, outputs, statuses, timestamps, preview snippets, and substitution review state.
- **FR-027**: The system MUST allow users to deanonymize newly pasted anonymized text inside an existing case by applying that case’s active mapping.
- **FR-028**: The system MUST display the deanonymized result directly inside the application and MUST allow the user to export that result with a friendly default filename.
- **FR-029**: When pasted text contains no matching substitutions from the active case mapping, the system MUST return the original pasted text unchanged and MUST clearly inform the user that no matches were applied.
- **FR-030**: The system MUST show readiness status in the main window in a simplified form with an optional detailed breakdown.
- **FR-031**: The system MUST block anonymization and deanonymization actions when readiness indicates that required local processing assets are unavailable.
- **FR-032**: The system MUST preserve the existing command-line behavior and MUST NOT require current CLI users to change commands, outputs, or workflows.
- **FR-033**: The system MUST reuse the existing service-layer anonymization, deanonymization, and readiness behaviors as the primary product authority rather than shelling out to the CLI.
- **FR-034**: The system MUST isolate any desktop-specific workflow extensions so that future fixes to anonymization/deanonymization contract behavior can be made without rewriting the whole UI feature.
- **FR-035**: The system MUST support only TXT processing in MVP while presenting document handling through an abstraction that can later support PDF, DOCX, and XLSX.
- **FR-036**: The system MUST keep all runtime processing local-only and MUST NOT require network access during normal runtime use.
- **FR-037**: The system MUST ship with local model assets already available to the application on first launch so that no runtime download is required.
- **FR-038**: The system MUST keep all cases until manual deletion and MUST require explicit user confirmation before deleting a case.
- **FR-039**: The system MUST preserve a per-case local job history that records anonymization runs, deanonymization actions, outcomes, and timestamps.
- **FR-040**: The system MUST mark outputs and review state clearly when they become outdated because the case mapping has been edited after the output was created.
- **FR-041**: The system MUST provide French-language user-facing copy for the MVP UI.
- **FR-042**: The system MUST provide a dark visual theme with a modern but simple presentation appropriate for non-technical legal users.
- **FR-043**: The system MUST make successful saved outputs discoverable from the currently selected case without requiring users to browse technical folder structures manually.
- **FR-044**: The system MUST preserve enough source-to-output linkage to identify which files and outputs were produced under each case and each run.
- **FR-045**: The system MUST produce actionable user-facing error states for per-file failures, blocked readiness, invalid pasted deanonymization input, and missing saved artifacts.
- **FR-046**: The system MUST allow reopening and later editing of substitution review state only when the underlying case data is sufficient to regenerate results safely.
- **FR-047**: The system MUST expose application identity assets so that product naming and iconography can be applied consistently in the window, executable, and distributed folder.
- **FR-048**: The system MUST provide a single main window composed at minimum of a persistent left-side case history panel, a central workspace for case files and outputs, a mapping/review area, a pasted-text deanonymization input area, and a result display area.
- **FR-049**: The system MUST provide a case-level status summary that allows the user to understand whether the selected case is currently healthy, partially failed, blocked, or contains stale outputs.
- **FR-050**: The system MUST show short preview snippets or equivalent identifying metadata, such as filename, bounded-length masked text, or both, so users can distinguish files within the current case while limiting unnecessary exposure of sensitive content.

### Non-Functional Requirements

- **NFR-001**: Representative non-technical legal users must be able to complete the quickstart primary workflows without command-line knowledge or manual model management.
- **NFR-002**: The application must remain responsive during sequential multi-file processing and MUST provide visible per-file progress and status updates.
- **NFR-003**: Default storage and file naming must let a user find the latest case outputs through the application and default export locations during quickstart validation without technical assistance.
- **NFR-004**: Case history and associated metadata must survive application restarts and standard Windows user sessions without requiring administrator rights.
- **NFR-005**: The product must remain fully usable in an offline environment after extraction of the portable distribution folder.
- **NFR-006**: The feature must not materially increase the risk of regression in the existing CLI and Python service workflows.
- **NFR-007**: The product must remain adaptable if later analysis reveals issues in anonymization/deanonymization contract coherence for the practical transformer backend.
- **NFR-008**: The product must minimize unnecessary duplication of sensitive original content and must avoid exposing more sensitive data than necessary in logs, previews, summaries, and persistent metadata.

### Architecture Constraints

- **AC-001**: The desktop experience MUST be implemented as a Windows desktop application using PySide6 with Qt Widgets.
- **AC-002**: The feature MUST remain Python-first and MUST NOT introduce Node.js, a browser-based frontend stack, Electron, or Tauri.
- **AC-003**: The desktop layer MUST integrate directly with `ReadinessService.get_readiness_report()`, `AnonymizationService.run(...)`, and `DeanonymizationService.run(...)` as the preferred integration points.
- **AC-004**: The UI layer MUST NOT duplicate anonymization or deanonymization business logic already owned by the current Python service layer and backend wrappers.
- **AC-005**: The practical supported backend for MVP MUST be treated as `transformer`; backend switching is not an MVP requirement.
- **AC-006**: Runtime execution MUST remain CPU-only, local-only, telemetry-free, auto-update-free, and network-free.
- **AC-007**: The architecture MUST define a document-adapter extension seam for future PDF, DOCX, and XLSX support without implementing those formats in this feature.
- **AC-008**: Desktop-specific data storage and review-state handling MUST be added in a way that does not break the current CLI and existing Python service behavior.
- **AC-009**: MVP TXT processing MUST be wired through the document-adapter seam so that future document formats can reuse the same application and service-layer workflow without moving business logic out of the service layer.

### Storage & Data Expectations

- **SD-001**: The system MUST store durable case metadata including at least display name, creation timestamp, last-opened timestamp, and deletion state.
- **SD-002**: The system MUST store durable per-case file records including source filename, source reference, processing status, timestamps, preview snippet, and links to saved outputs.
- **SD-003**: The system MUST store durable per-case job records for anonymization and deanonymization actions, including outcome status and user-visible error summaries when relevant.
- **SD-004**: The system MUST store a persistent case-level substitution state that supports later case reopening, substitution review, removal decisions, and pasted deanonymization.
- **SD-005**: The system MUST store mapping version information or equivalent durable change-tracking metadata sufficient to identify each meaningful change to the active case mapping.
- **SD-006**: The system MUST store enough metadata to determine whether a saved output is current or stale relative to the latest case mapping version or equivalent change-tracking state.
- **SD-007**: The system MUST use Windows-friendly local storage locations for internal case data and user-facing outputs.
- **SD-008**: The system MUST separate internal durable application metadata from user-facing exported artifacts in a way that remains understandable to end users.
- **SD-009**: The system MUST retain references to the authoritative saved artifacts used by the case so that the application can reopen and inspect prior work without rescanning arbitrary folders.
- **SD-010**: The system MUST support user-friendly default filenames for anonymized outputs, case mapping artifacts, and exported deanonymized text.
- **SD-011**: The preferred storage design SHOULD use a lightweight local database for case metadata, job records, mapping state, and indexing concerns, while storing user-facing text artifacts and other exported outputs as files.
- **SD-012**: The durable directory structure MUST clearly separate application metadata, case-managed working data, and user-facing exported artifacts.
- **SD-013**: Each output artifact record MUST retain the mapping version or equivalent change-tracking reference that was active when the artifact was generated.
- **SD-014**: The storage model MUST retain enough linkage to determine which prior outputs are impacted when a case substitution is removed or otherwise changed.

### Packaging Requirements

- **PR-001**: The feature MUST produce a portable standalone Windows distribution that runs from an extracted folder without requiring a separate server process.
- **PR-002**: The portable distribution MUST include the executable, required application assets, and local model assets under an application `models/` directory.
- **PR-003**: First launch of the portable distribution MUST NOT download models, dependencies, or application content from the network.
- **PR-004**: The preferred packaging approach MUST be PyInstaller unless a different Python-only packaging approach provides a stronger portable outcome without violating other constraints.
- **PR-005**: The distribution MUST support user-friendly product naming and icon assets.
- **PR-006**: The feature MUST include packaging or build scripts and developer-facing build instructions sufficient to reproduce the portable distribution.
- **PR-007**: For portability of the extracted distribution folder, required model paths MUST resolve relative to the application root directory rather than relying on machine-specific absolute paths.
- **PR-008**: Readiness MUST fail clearly and actionably when required local model files are missing, incomplete, or corrupted in the portable distribution.

### Testing Requirements

- **TR-001**: The feature MUST include unit tests for new case-domain logic, storage behavior, filename generation, mapping update behavior, and readiness-state presentation logic.
- **TR-002**: The feature MUST include UI tests covering case creation, case reopening from history, file selection, batch progress display, substitution review, pasted deanonymization, and deletion confirmation flows.
- **TR-003**: The feature MUST include integration tests proving that the desktop layer reuses the existing Python service layer directly rather than shelling out to the CLI.
- **TR-004**: The feature MUST include regression tests proving that current CLI behavior remains unchanged.
- **TR-005**: The feature MUST include round-trip tests for anonymization and deanonymization coherence using the practical transformer-supported workflow.
- **TR-006**: The feature MUST include tests covering shared case mapping across multiple files processed under the same case.
- **TR-007**: The feature MUST include tests covering later deanonymization of newly pasted anonymized text using an existing case mapping.
- **TR-008**: The feature MUST include tests covering substitution removal, regenerated anonymized output, and persistent case-mapping updates after the removal.
- **TR-009**: The feature MUST include tests covering partial batch failure behavior in which one file fails and remaining files still complete.
- **TR-010**: The feature MUST include tests covering reopening a case after restart and confirming that files, outputs, statuses, and review state remain available.
- **TR-011**: The feature MUST include Windows packaging smoke tests that validate the portable extracted distribution launches, loads local models, and performs at least one TXT anonymization workflow without network access.

### Key Entities *(include if feature involves data)*

- **Case (Dossier)**: A durable legal-matter workspace that owns the shared substitution state, associated source files, local outputs, local job history, readiness context, and reopened session context.
- **Case Mapping**: The authoritative substitution set for a case, including current active replacements, removal decisions, versioning or equivalent staleness tracking, and references needed for later deanonymization.
- **Case Document**: A source TXT file associated with a case, including its display information, source reference, processing status, preview snippet, timestamps, and related output artifacts.
- **Job Record**: A logged user-triggered operation within a case, such as anonymization of one or more files or pasted deanonymization, including timestamps, outcomes, and error summaries.
- **Output Artifact**: A saved anonymized text, mapping artifact, or exported deanonymized text associated with a case and one or more job records, including filename, path, creation time, and freshness state.
- **Review Decision**: A user action that removes a substitution from the active review set and triggers regeneration or state invalidation for affected outputs.

### Assumptions

- Existing CLI and service-layer behavior is treated as the baseline product contract and must remain available during and after this feature.
- Automatic saving uses application-managed default locations so the default user flow does not require manual path selection.
- Case deletion is permanent from the user-facing product perspective once confirmed, even if the internal persistence layer uses a soft-delete flag with no recovery flow exposed in MVP.
- Reopening and later editing of substitution review state is allowed only when the case retains the data required to regenerate outputs safely.
- Internal storage may separate app-managed metadata from user-facing exported files as long as both remain discoverable through the UI.
- If deanonymization can only partially restore pasted text, the product still considers the workflow successful provided the result is clearly labeled and export remains available.

### Anti-Scope

- The feature does not add PDF, DOCX, or XLSX processing in MVP.
- The feature does not introduce multiple practical runtime backends or backend switching controls in MVP.
- The feature does not require user accounts, online collaboration, cloud storage, telemetry, or auto-update services.
- The feature does not require a browser-based frontend, Node.js runtime, or web deployment target.
- The feature does not allow users to create arbitrary new substitutions manually in the review interface.
- The feature does not replace or remove the existing CLI workflow.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In usability testing with representative non-technical legal users, at least 90% can create or open a case and anonymize one TXT file without external assistance.
- **SC-002**: In the default flow, a user can start from application launch and complete anonymization of a single TXT file into a saved case in 3 minutes or less.
- **SC-003**: In a sequential batch of 10 valid TXT files, users can observe per-file status for the entire run and access all successful outputs without rerunning the whole batch because of a single-file failure.
- **SC-004**: After closing and reopening the application, 100% of retained test cases remain reopenable with their files, outputs, statuses, and saved substitution review state intact.
- **SC-005**: In acceptance testing, users can paste anonymized text into an existing case and obtain an in-app deanonymized result with export available in under 1 minute.
- **SC-006**: In pilot validation, at least 90% of substitution removals performed through the review workflow produce the expected regenerated text and updated persistent case state without requiring manual file editing.
- **SC-007**: The desktop feature ships without breaking the existing CLI regression suite for current anonymization, deanonymization, and readiness behaviors.
