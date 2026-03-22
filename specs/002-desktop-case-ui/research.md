# Research: A4 Desktop Case Workspace

## Decision 1: Desktop integration must call the service layer directly

- **Decision**: Implement a desktop workspace layer that calls `ReadinessService.get_readiness_report()`, `AnonymizationService.run(...)`, and `DeanonymizationService.run(...)` directly through desktop-facing orchestration services.
- **Rationale**: The spec explicitly prohibits shelling out to the CLI and requires current service behavior to remain the product authority. This keeps desktop and CLI behavior aligned and limits regression risk.
- **Alternatives considered**:
  - Shell out to the CLI from the desktop app: rejected because it violates the spec and would make error handling, progress, and testing brittle.
  - Reimplement anonymization logic in the UI layer: rejected because it breaks engine reuse and would fork behavior from the validated service layer.

## Decision 2: Use lightweight metadata storage plus file-based artifact storage

- **Decision**: Persist case metadata, job records, mapping revision state, and indexing information in a lightweight local database, while storing anonymized text, mapping snapshots, and exported deanonymized text as files.
- **Rationale**: The spec requires durable case history, stale-output tracking, mapping versioning, and later reopening. Those concerns become error-prone in ad hoc nested JSON alone, especially once many cases, jobs, and output relationships accumulate. A lightweight metadata database keeps queries and version tracking deterministic while preserving simple file-based user artifacts.
- **Alternatives considered**:
  - JSON-only case storage: rejected because cross-linking outputs, mapping revisions, stale states, and batch jobs would become fragile and hard to migrate.
  - Full client-server database setup: rejected because it violates the local-first, portable, low-complexity requirements.

## Decision 3: Split storage by purpose on Windows

- **Decision**: Store internal metadata and app-managed working state under a Windows AppData location, and store user-facing exported artifacts in a Windows-friendly documents location, with packaged models resolved from the extracted application root.
- **Rationale**: This keeps internal metadata durable and hidden from casual tampering while placing user-facing deliverables in a location that non-technical users can easily find. It also preserves portable packaged runtime behavior because models travel with the extracted app folder rather than depending on machine-specific cache paths.
- **Alternatives considered**:
  - Keep everything only inside the extracted portable folder: rejected because portable folders are often moved, duplicated, or deleted and are a poor place for durable user history.
  - Keep everything only in AppData: rejected because user-facing exports become harder for legal users to find and manage.

## Decision 4: Case mapping conflict rule must be deterministic and case-stable

- **Decision**: Within a case, the first active mapping established for a given original entity becomes the stable case pseudonym unless the user explicitly removes that substitution. Later conflicting pseudonyms for the same original entity are resolved deterministically in favor of the already active case mapping.
- **Rationale**: The spec requires one stable pseudonym per original entity within a case and prohibits silent multi-pseudonym drift. Using the earliest established active mapping is deterministic, easy to explain, and compatible with case continuity across files.
- **Alternatives considered**:
  - Prefer newest mapping each time: rejected because it makes previously generated outputs unstable and undermines case continuity.
  - Prompt the user for every conflict immediately: rejected for MVP because it adds friction to the main workflow and complicates sequential batch processing.

## Decision 5: Mapping changes need explicit revision tracking

- **Decision**: Represent case mapping evolution with a monotonic revision number or equivalent append-only change-tracking scheme. Every output artifact and deanonymization action records the mapping revision used at generation time.
- **Rationale**: The spec requires stale-output detection, affected-output marking, and later reopening. Explicit revision tracking is the simplest robust way to answer “which outputs are current?” and “which outputs became stale after this removal?”
- **Alternatives considered**:
  - Only store a last-modified timestamp: rejected because timestamps alone make impacted-output reasoning and deterministic stale detection weaker.
  - Recompute freshness by diffing free-form mapping blobs each time: rejected because it is more complex and less auditable than explicit revision linkage.

## Decision 6: Substitution removal should mark impacted outputs stale rather than overwrite them

- **Decision**: When a user removes a substitution from the active case mapping, previously generated outputs that depended on that substitution are marked stale and remain accessible until the user chooses to regenerate.
- **Rationale**: Silent destructive regeneration would obscure audit history and risk surprising legal users. Marking artifacts stale preserves traceability and lets users control when to refresh outputs.
- **Alternatives considered**:
  - Automatically regenerate all prior outputs: rejected because it is opaque, can be expensive, and risks overwriting artifacts the user may still need for comparison.
  - Leave old outputs marked current: rejected because it violates the spec’s coherence and stale-state requirements.

## Decision 7: Zero-match pasted deanonymization should succeed with an unchanged result

- **Decision**: When pasted deanonymization input contains no matches from the active case mapping, the result is the unchanged input and the session is labeled as a no-match outcome rather than an error.
- **Rationale**: The spec requires explicit zero-match handling, and this behavior is easy for users to understand. It also avoids false failure states when the pasted text simply has no known case substitutions.
- **Alternatives considered**:
  - Treat zero matches as an error: rejected because it conflates a valid no-op with system failure.
  - Suppress the result view entirely: rejected because users need visible confirmation that nothing was changed.

## Decision 8: The main window should stay single-screen but functionally partitioned

- **Decision**: Use one main window with four minimum functional regions: persistent case history on the left, central case workspace for files/outputs, a review/mapping area, and a pasted deanonymization input/output area.
- **Rationale**: This matches the spec’s single-window simplicity while giving each core workflow a stable home, reducing navigation overhead for non-technical users.
- **Alternatives considered**:
  - Multi-window workflow: rejected because it complicates a lawyer-facing MVP.
  - Pure tab-based isolated tools: rejected because it weakens the “case as workspace” concept and can hide relationships between outputs and mapping state.

## Decision 9: Portable model resolution must be relative to application root

- **Decision**: The portable desktop build resolves required model paths from the extracted application root and fails readiness clearly if required model assets are missing, incomplete, or corrupted.
- **Rationale**: The spec requires no first-launch downloads and portable extracted-folder execution. Root-relative resolution is the most reliable way to keep packaged models portable across Windows machines.
- **Alternatives considered**:
  - Depend on global Hugging Face cache discovery only: rejected because it breaks portability and first-launch predictability.
  - Download on first launch: rejected because it violates explicit runtime constraints.

## Decision 10: UI and packaging verification require dedicated test layers

- **Decision**: Add UI automation for Qt workflows, packaging smoke tests for the portable build, and regression coverage proving the CLI remains unaffected.
- **Rationale**: The feature crosses desktop UI, persistence, packaging, and existing domain behavior. Existing unit/integration tests alone are insufficient to prove the packaged workflow or case UX.
- **Alternatives considered**:
  - Rely only on manual desktop QA: rejected because it would not protect deterministic mapping, stale-state logic, or packaging regressions adequately.
