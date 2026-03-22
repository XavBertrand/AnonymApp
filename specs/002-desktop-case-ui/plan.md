# Implementation Plan: A4 Desktop Case Workspace

**Branch**: `002-desktop-case-ui` | **Date**: 2026-03-22 | **Spec**: [/home/xavier/PycharmProjects/AnonymApp/specs/002-desktop-case-ui/spec.md](/home/xavier/PycharmProjects/AnonymApp/specs/002-desktop-case-ui/spec.md)
**Input**: Feature specification from `/specs/002-desktop-case-ui/spec.md`

## Summary

Deliver a single-window Windows desktop workspace for case-based TXT anonymization and pasted-text deanonymization that reuses the current Python service layer directly, preserves CLI behavior, keeps runtime fully local and CPU-only, and introduces durable case storage with deterministic shared mapping, mapping-version tracking, stale-output detection, and portable packaged model resolution. The desktop UI will integrate only through an explicit `CaseWorkspaceService` (or equivalently named orchestration service) that centralizes case lifecycle (`create`, `load`, `delete`), mapping revision management, deterministic conflict handling, batch anonymization orchestration, substitution review and removal workflows, stale-state propagation, deanonymization sessions, and persistence coordination. TXT processing in MVP will be routed through an explicit document-adapter seam so future PDF/DOCX/XLSX adapters can plug into the same orchestration flow without moving business logic out of the service layer.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: Existing anonymization stack (`transformers`, `torch`, `rapidfuzz`, `Unidecode`, `gliner`); planned desktop/runtime additions `PySide6`, `PyInstaller`; planned test additions `pytest-qt`  
**Storage**: Lightweight local metadata database plus filesystem artifact storage; internal metadata under Windows AppData, case-managed working data under app-managed local storage, user-facing exports under a Windows-friendly documents location; packaged models resolved from `models/` relative to the application root  
**Testing**: `pytest`, existing unit/integration/contract suites, planned `pytest-qt` UI tests, packaging smoke scripts for portable Windows distribution  
**Target Platform**: Portable standalone Windows 10/11 x64 desktop distribution runnable from an extracted folder  
**Project Type**: Python desktop application layered on top of an existing CLI and service library  
**Performance Goals**: Non-binding engineering targets are: main window becomes usable within 5 seconds on a reference Windows workstation with local models present; case switching and readiness refresh feel immediate (<1 second target); first visible progress/status update appears within 1 second of starting a multi-file run; desktop overhead remains negligible relative to current anonymization runtime  
**Constraints**: Preserve current CLI behavior; no CLI shell-out from desktop; desktop additions must not alter CLI outputs or workflows; shared processing logic must remain centralized; local-only, CPU-only, offline runtime; no Node.js/Electron/Tauri; TXT-only MVP; deterministic case mapping; TXT must flow through a document-adapter seam even in MVP; model paths must be portable relative to the extracted application root; no telemetry or auto-update; UI must not contain business logic for mapping, conflict resolution, revisioning, or stale detection  
**Scale/Scope**: Single-user desktop app; one main window; dozens to hundreds of saved cases; tens of TXT files per case; sequential multi-file runs; repeated reopening and later deanonymization using case mapping history

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Gate

- **Engine Reuse First**: Pass. The plan reuses `ReadinessService`, `AnonymizationService`, and `DeanonymizationService` as the authoritative business layer. Existing anonymization scripts and wrappers remain orchestrated, not rewritten. Shared desktop and CLI behavior stays centralized rather than duplicated.
- **Layered Architecture**: Pass. Planned touched layers are `ui` (`src/app/desktop/`), `application/service` (`src/services/` case orchestration additions centered on `CaseWorkspaceService`), `engine abstraction` (existing wrappers unchanged except compatibility-safe extensions if needed), `document adapter` (existing TXT adapter plus future extension seam), and `storage/config` (new case persistence and portable path resolution). The UI will not access persistence adapters or mapping state directly and will consume only orchestration-service view models/DTOs.
- **Stable Engine Interface**: Pass. The desktop feature depends on the common wrapper/service contracts and does not introduce backend-specific UI execution paths. Any compatibility fix required for mapping coherence must remain backward-safe for current service consumers.
- **Incremental Delivery**: Pass. Increment 1: launch desktop shell and packaging scaffolding. Increment 2: introduce additive desktop persistence, TXT adapter seam, and foundational orchestration. Increment 3: case creation/open + case list + multi-file batch + history persistence. Increment 4: substitution review/removal + regeneration + stale-state handling. Increment 5: pasted deanonymization + export + simplified readiness UX + packaging smoke. Each increment is rollback-safe because the CLI remains untouched, desktop entrypoints stay additive, and new persisted desktop state remains isolated from existing CLI runtime artifacts.
- **Local-First**: Pass. Core workflows remain local, offline, CPU-only, and model-backed from packaged local assets.
- **Deterministic + Auditable**: Pass. The plan introduces case mapping versioning, deterministic conflict resolution, per-artifact mapping references, stale-state tracking, and durable job records. `MappingRevision` is treated as the single source of truth, earliest-established mapping wins on conflict unless a user review changes it, and stale-state propagation is automatically triggered whenever mapping changes occur.
- **Robust Error Handling**: Pass. Planned failure handling covers missing/corrupt models, blocked readiness, invalid/missing source files, per-file batch failures, stale outputs, unsupported input, and zero-match pasted deanonymization.
- **Testability**: Pass. The plan includes unit, integration, UI, packaging smoke, and CLI regression coverage with deterministic mapping and stale-output checks, including explicit tests proving deterministic conflict resolution across multiple files and identical mapping outcomes across repeated runs for identical inputs.
- **Extensibility**: Pass. TXT remains the only implemented document type, but document handling remains behind adapter seams so future PDF/DOCX/XLSX support can be added without changing case workflows.
- **Minimal Invasive Changes**: Pass. Existing anonymization scripts are preserved. Desktop-specific behavior is added through orchestration, persistence, and UI layers, with only minimal compatibility-safe service additions where required. Persistence adapters remain thin and workflow-free.

### Post-Design Check

- **Engine Reuse First**: Pass. Research and design keep the existing service layer as the only processing authority and add a desktop-facing `CaseWorkspaceService` facade rather than alternate execution paths. CLI safety remains preserved because shared logic stays centralized.
- **Layered Architecture**: Pass. Data model and contracts separate desktop presentation, case orchestration, persistence, and existing engine-backed services. The UI consumes DTOs/view models only and does not bind directly to persistence entities, mapping snapshots, or storage adapters.
- **Stable Engine Interface**: Pass. Design keeps engine calls behind current service and wrapper boundaries; any mapping-coherence fix is scoped as a service/storage concern with regression protection for the CLI.
- **Incremental Delivery**: Pass. The designed entities and contracts support staged delivery without requiring a large one-shot rewrite.
- **Local-First**: Pass. Portable packaging, root-relative models, and readiness failure handling preserve offline local execution.
- **Deterministic + Auditable**: Pass. Mapping revisions, output artifact version references, and case/job records provide auditable traceability. `MappingRevision` remains the single source of truth, deterministic conflict resolution is centralized in the application/service layer, and stale-state propagation is automatically triggered on mapping change with no UI-local divergence.
- **Robust Error Handling**: Pass. Contracts define actionable error outcomes for blocked readiness, per-file failures, stale outputs, zero-match deanonymization, and deleted/missing artifacts.
- **Testability**: Pass. The design supports isolated tests for persistence, mapping revision logic, deterministic conflict resolution, review/regeneration, stale propagation, UI workflows, packaging, and CLI regression safety.
- **Extensibility**: Pass. Data model and project structure explicitly leave room for future document adapters without altering the case concept.
- **Minimal Invasive Changes**: Pass. No direct core engine rewrite is required by the design. Persistence remains data-focused and free of workflow or mapping logic.

## Project Structure

### Documentation (this feature)

```text
specs/002-desktop-case-ui/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── desktop-workspace-contract.md
│   └── case-artifact-layout-contract.md
└── tasks.md
```

## Increment Plan & Rollback Safety

1. **Increment 1 - Desktop shell and packaging scaffolding**
   - Scope: desktop bootstrap, main window shell, worker/presenter scaffolding, optional packaging/build scripts.
   - Rollback-safe boundary: the application remains runnable through the existing CLI only if this increment is reverted; no persistence schema or case data is required for the CLI path.
   - Revert safety: remove desktop entrypoint/package hooks and packaging artifacts without touching engine logic, runtime outputs, or existing CLI commands.
2. **Increment 2 - Additive desktop persistence, TXT document-adapter seam, and foundational orchestration**
   - Scope: metadata database bootstrap, additive desktop storage schema, document-adapter contract under `src/adapters/documents/`, TXT adapter registration/wiring, foundational service orchestration, and readiness plumbing.
   - Rollback-safe boundary: new tables/files are used only by the desktop feature and are isolated from current CLI runtime directories and outputs.
   - Revert safety: disable desktop persistence/adapter wiring while leaving any created desktop metadata untouched or ignored; no destructive migration is required and no CLI behavior changes.
3. **Increment 3 - Case lifecycle, case list, sequential batch anonymization, and history**
   - Scope: `CaseWorkspaceService` case lifecycle, case list/history UI, sequential multi-file orchestration, case/job/artifact persistence.
   - Rollback-safe boundary: desktop case records are additive; reverting this increment leaves previously stored desktop data unread by the disabled feature but does not corrupt existing anonymization outputs or CLI flows.
   - Revert safety: remove orchestration/UI layers while preserving existing files and persisted desktop records as inert data.
4. **Increment 4 - Mapping revision management, substitution review, and stale-state handling**
   - Scope: mapping revisions, deterministic conflict resolution, substitution removal, stale-state propagation, explicit stale-output regeneration workflow, editability eligibility checks.
   - Rollback-safe boundary: revision/stale metadata is additive and case-scoped; existing anonymized artifacts remain readable even if stale features are later disabled.
   - Revert safety: freeze desktop cases at the last persisted revision state without affecting CLI outputs, service-layer engine calls, or previously generated case artifacts.
5. **Increment 5 - Pasted deanonymization, simplified readiness UX, export, and portable packaging validation**
   - Scope: deanonymization sessions, simplified readiness UX, export workflow, portable packaging validation, root-relative model resolution checks.
   - Rollback-safe boundary: deanonymization session records and packaging assets are additive and separate from core anonymization persistence.
   - Revert safety: remove desktop deanonymization/export entrypoints or packaging scripts without affecting existing cases, mappings, or CLI commands.

### Source Code (repository root)

```text
src/
├── adapters/
│   ├── documents/           # new: document-adapter contract + TXT adapter registration seam
│   ├── mappings/
│   └── persistence/         # new: thin case metadata and artifact persistence adapters
├── app/
│   ├── cli/
│   ├── desktop/             # new: Qt Widgets application shell, presenters, dialogs, view models
│   └── ui_contracts/
├── bootstrap/
├── config/
├── engines/
├── models/
└── services/                # existing services + new CaseWorkspaceService orchestration layer

tests/
├── contract/
├── integration/
├── packaging/               # new: portable build smoke tests
├── ui/                      # new: Qt UI tests
└── unit/

scripts/
└── packaging/               # new: build/package helpers
```

**Structure Decision**: Keep the existing single Python project and add a desktop UI layer plus persistence support inside the current repository. The desktop UI will interact only with `CaseWorkspaceService` (or an equivalently named orchestration service) that owns case lifecycle, mapping revision management, deterministic conflict resolution, stale propagation, batch anonymization workflows, deanonymization session handling, and persistence coordination. TXT input will enter the system through a document-adapter seam under `src/adapters/documents/`; future formats can attach there without changing service boundaries. Persistence adapters remain thin and data-focused, while business rules stay in the application/service layer. This minimizes invasive change, preserves the CLI/service layout, and keeps the case workspace close to the current domain code instead of creating a separate frontend project.

## Complexity Tracking

No constitution violations requiring justification at plan time.
