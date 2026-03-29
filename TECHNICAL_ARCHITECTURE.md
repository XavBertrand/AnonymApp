# AnonymApp Technical Architecture

This document is written for a coding LLM or engineer who needs to understand the repository quickly, modify it safely, and improve it without breaking the current product.

It documents the repository as it exists today, not an idealized target architecture. When code and old docs disagree, trust the code first and use tests to confirm behavior.

## 1. What this repository currently is

AnonymApp is a local-first text anonymization application with two coexisting product surfaces:

- a legacy but still supported CLI flow
- a newer desktop case-management flow built around PySide6

The repository is not a generic platform yet. The abstractions suggest multi-backend and multi-document support, but the implemented production path is still narrow:

- document format: `.txt`
- primary backend: `transformer`
- model family: GLiNER-based local transformer flow
- execution mode: local, CPU-only at wrapper level
- reversible flow: anonymize text, persist a canonical mapping artifact, later deanonymize

The most important architectural reality is this:

- the desktop app is now the richest and most actively developed path
- the CLI still exists and uses a simpler runtime/storage model
- both rely on the same core engine wrapper and readiness subsystem

## 2. How to read the repo

If you are a coding LLM, the fastest accurate reading order is:

1. Read this file.
2. Read `README.md` for setup and user-facing scope.
3. Read `src/app/desktop/main.py` and `src/app/desktop/window.py` to understand the current primary UI shell.
4. Read `src/services/case_workspace_service.py` to see the composition root for desktop behavior.
5. Read `src/services/anonymization_service.py`, `src/services/deanonymization_service.py`, and `src/services/readiness_service.py`.
6. Read `src/engines/transformer_wrapper.py` and the bundled scripts in `tmp/`.
7. Read `src/adapters/persistence/database.py` and `src/adapters/persistence/artifact_store.py`.
8. Read the relevant tests for the area you are changing.

If you are changing packaging, read `scripts/packaging/` next. If you are changing intended product behavior, inspect `specs/001-*` and `specs/002-*` after reading the runtime code.

## 3. Repository map

The repository is organized around a fairly standard layered Python layout plus planning artifacts and Windows packaging helpers.

```text
.
|-- AGENTS.md                          Repo-specific instructions for coding agents
|-- README.md                          Quick user/developer overview
|-- TECHNICAL_ARCHITECTURE.md          This document
|-- pyproject.toml                     Python package metadata and dependencies
|-- uv.lock                            Locked dependency set for uv-based workflows
|-- requirements-windows.txt           Windows build-time dependency install path
|-- src/                               Application source code
|   |-- app/
|   |   |-- cli/                       CLI entrypoint
|   |   |-- desktop/                   Desktop UI, widgets, presenter, worker, Qt compatibility
|   |   `-- ui_contracts/              View-model dataclasses consumed by the desktop UI
|   |-- adapters/
|   |   |-- documents/                 Document format adapters, currently TXT only
|   |   |-- mappings/                  Canonical mapping artifact adapter
|   |   `-- persistence/               SQLite repositories and filesystem artifact store
|   |-- bootstrap/                     Readiness/dependency/model checks
|   |-- config/                        Paths, env vars, logging, runtime setup
|   |-- engines/                       Engine wrapper contracts and transformer wrapper
|   |-- models/                        Cross-layer canonical data models
|   `-- services/                      Business orchestration and desktop workflow logic
|-- tests/
|   |-- unit/                          Isolated unit tests
|   |-- integration/                   Cross-layer application flow tests
|   |-- ui/                            Desktop widget/window tests
|   |-- packaging/                     Packaging and portable bundle tests
|   |-- contract/                      Explicit engine/interface contract tests
|   `-- helpers/                       Test fakes and utilities
|-- scripts/
|   `-- packaging/                     Windows portable build/staging/verification scripts
|-- tmp/                               Bundled backend scripts dynamically loaded by wrappers
|-- runtime/                           Generated local runtime data for non-desktop flows
|-- models/                            Local model assets expected by desktop packaging flows
|-- out/                               Generated release staging output
`-- specs/                             Feature specs, research, tasks, contracts
```

Important non-code directories:

- `specs/001-build-desktop-anonymizer/`: early CLI/MVP planning
- `specs/002-desktop-case-ui/`: current desktop/case-management planning, contracts, quickstart
- `models/`: local model payload expected for packaging and readiness in desktop portable workflows
- `out/`: generated staging output for Windows test releases, not core source code

## 4. High-level architecture

At runtime, the dependency direction is roughly:

```text
UI / CLI entrypoints
  -> presenter or command handler
    -> services
      -> adapters/repositories
        -> filesystem + SQLite
      -> readiness bootstrap
      -> engine wrappers
        -> tmp backend scripts
```

The most important layers are:

### 4.1 Entry points

- `src/app/cli/main.py`
- `src/app/desktop/main.py`

These are thin. They initialize logging/runtime, build services, and dispatch work.

### 4.2 UI layer

- `src/app/desktop/window.py`
- `src/app/desktop/widgets/*`
- `src/app/desktop/presenters/workspace_presenter.py`
- `src/app/ui_contracts/case_workspace_view_models.py`

The desktop window is a fairly "thick" orchestrator: it wires widgets together, handles async callbacks, tracks local UI state, and calls the presenter. The presenter is intentionally thin and mostly forwards to the main service.

### 4.3 Service layer

- `src/services/case_workspace_service.py`
- `src/services/case_batch_service.py`
- `src/services/substitution_review_service.py`
- `src/services/stale_output_regeneration_service.py`
- `src/services/pasted_deanonymization_service.py`
- `src/services/anonymization_service.py`
- `src/services/deanonymization_service.py`
- `src/services/readiness_service.py`

This is the true center of the application. Most business rules live here.

### 4.4 Adapter and persistence layer

- `src/adapters/documents/*`
- `src/adapters/mappings/*`
- `src/adapters/persistence/*`

This layer isolates file formats, SQLite access, and artifact path decisions.

### 4.5 Engine and backend integration layer

- `src/engines/base.py`
- `src/engines/transformer_wrapper.py`
- `tmp/transformer_anonymizer.py`
- `tmp/anonymizer.py`

This is where the app bridges into the actual anonymization implementation.

### 4.6 Bootstrap/configuration layer

- `src/bootstrap/*`
- `src/config/*`

This layer resolves runtime paths, readiness checks, logging, and model/dependency discovery.

## 5. Source tree in detail

### 5.1 `src/app/cli/`

The CLI exposes three commands:

- `readiness`
- `anonymize`
- `deanonymize`

It is intentionally simple and still useful for smoke testing the core engine path. It uses the older `runtime/outputs`, `runtime/mappings`, and `runtime/logs` layout from `src/config/settings.py`.

### 5.2 `src/app/desktop/`

This is the main desktop product surface.

Key files:

- `main.py`: builds the main window and starts Qt
- `window.py`: top-level UI composition and event handling
- `qt_compat.py`: real PySide6 imports when available, stub Qt classes otherwise
- `workers/workspace_worker.py`: single-thread `ThreadPoolExecutor` used for background jobs
- `copy/fr.py`: French UI strings
- `widgets/*`: individual panels for readiness, case list, workspace, review, preview, deanonymization

Important nuance:

- the desktop UI can run in environments without real PySide6 because `qt_compat.py` provides stubs for tests
- this makes tests easy to run, but also means some UI tests are not exercising real Qt behavior

### 5.3 `src/app/ui_contracts/`

This directory contains frozen dataclasses that define the view-model contract between services and widgets.

These dataclasses are a good "stability seam". If you are refactoring internals but want to preserve UI behavior, keep these shapes stable or migrate them deliberately with tests.

### 5.4 `src/services/`

This directory contains the application's business logic. It is the most important place to understand before making behavioral changes.

Key responsibilities:

- `anonymization_service.py`: single-file anonymization
- `deanonymization_service.py`: mapping-driven deanonymization
- `readiness_service.py`: cached readiness reporting and enforcement
- `case_workspace_service.py`: desktop composition root and facade for the whole case-management workflow
- `case_batch_service.py`: batch anonymization into a case
- `mapping_revision_service.py`: revisioned per-case mapping state
- `substitution_review_service.py`: review/removal of substitutions from current outputs
- `stale_state_service.py`: trust and staleness decisions
- `stale_output_regeneration_service.py`: regenerate outputs affected by mapping revisions
- `pasted_deanonymization_service.py`: deanonymize pasted anonymized text using active case mappings
- `artifact_maintenance_service.py`: mark missing tracked files and clean temp artifacts
- `privacy_guard.py`: preview/readiness data redaction helpers
- `desktop_error_translator.py`: translate low-level failures into desktop-friendly messages

### 5.5 `src/adapters/documents/`

Currently only TXT is supported.

- `txt_adapter.py`: load/save plain text
- `registry.py`: resolve adapter by path/format
- `contract.py`: adapter interface contract

The registry exists to support future document types, but the repo is not yet multi-format in practice.

### 5.6 `src/adapters/mappings/`

- `canonical_mapping_adapter.py`

This adapter loads and dumps the canonical mapping artifact format used across anonymization, deanonymization, review, and regeneration.

### 5.7 `src/adapters/persistence/`

This folder combines SQLite metadata repositories and filesystem artifact storage.

Key files:

- `database.py`: SQLite schema bootstrap and simple migration-by-bootstrap logic
- `artifact_store.py`: case directory naming and artifact file path generation
- `records.py`: repository-level record dataclasses
- `case_repository.py`
- `document_repository.py`
- `mapping_revision_repository.py`
- `artifact_repository.py`
- `job_repository.py`
- `deanonymization_session_repository.py`
- `review_decision_repository.py`

The repositories are relatively thin and table-oriented.

### 5.8 `src/engines/`

- `base.py`: wrapper protocol / init config
- `transformer_wrapper.py`: current production wrapper
- `classic_wrapper.py`: legacy/alternate path support still present in code/tests

The production app path is the transformer wrapper.

### 5.9 `src/bootstrap/`

Readiness checks are assembled here.

- `dependency_check.py`: Python module availability checks
- `model_check.py`: local/HF model presence checks
- `readiness_bootstrap.py`: convert raw checks into `BackendDescriptor`s

### 5.10 `src/config/`

- `settings.py`: project root and CLI/runtime paths
- `desktop_settings.py`: desktop data roots, export roots, app root, packaged models path
- `logging.py`: logging configuration and user-facing error translation

### 5.11 `src/models/`

These are cross-layer data contracts:

- `canonical_result.py`: in-memory anonymization result
- `mapping_artifact.py`: persisted canonical mapping artifact
- `backend_descriptor.py`: readiness and backend state

### 5.12 `scripts/packaging/`

This folder contains the Windows portable build/staging flow.

Important files:

- `build_windows.ps1`: final Windows build entrypoint
- `build_windows_portable.py`: packaging plan, hidden imports, datas, runtime DLL lookup
- `a4_desktop.spec`: PyInstaller spec
- `smoke_test_portable.py`: bundle layout/path smoke checks
- `prepare_windows_test_release.py`: stage a Windows-ready release folder from Linux/WSL
- `verify_staged_release.py`: validate the staged folder before copying/building

### 5.13 `tmp/`

These scripts are loaded dynamically by the transformer wrapper.

- `tmp/transformer_anonymizer.py`
- `tmp/anonymizer.py`

This is one of the most important architectural compromises in the repo. They are not normal package modules; they are runtime-loaded implementation files that packaging must carry along.

## 6. Runtime and storage layout

There are two related but different storage models in the repository.

### 6.1 CLI/runtime layout

Defined in `src/config/settings.py`:

- `runtime/outputs`
- `runtime/mappings`
- `runtime/logs`

This layout is used by the legacy CLI and simple service calls.

### 6.2 Desktop data layout

Defined in `src/config/desktop_settings.py`:

- desktop metadata DB: `runtime/desktop/metadata.sqlite3` by default
- case root: `runtime/desktop/cases/`
- exports root: `runtime/desktop/exports/`

Each case gets a slugged directory:

```text
runtime/desktop/cases/<slug>-<case_id_prefix>/
|-- imports/
|-- outputs/
|-- mappings/
`-- sessions/
```

This split matters:

- imported source copies live under `imports/`
- anonymized outputs live under `outputs/`
- canonical mapping JSONs live under `mappings/`
- pasted deanonymization session input/result files live under `sessions/`
- exported deanonymized user-facing files go to the exports root, not inside the case working area

### 6.3 Environment-variable controlled roots

Key environment variables:

- `ANONYMAPP_APP_ROOT`
- `ANONYMAPP_DESKTOP_DATA_ROOT`
- `ANONYMAPP_DESKTOP_EXPORT_ROOT`
- `ANONYMAPP_TRANSFORMER_MODEL_PATH`
- `HF_HOME`
- `ANONYMAPP_FORCE_QT_OFFSCREEN`
- `ANONYMAPP_FORCE_QT_STUBS`

Meaning:

- app root controls where packaged models are resolved in desktop/portable mode
- desktop data root controls where SQLite and case-managed working files live
- desktop export root controls where user-visible deanonymized exports are written
- transformer model path can override model lookup
- Qt env vars are used for headless/test behavior

## 7. SQLite metadata schema

`src/adapters/persistence/database.py` creates and maintains the SQLite schema on startup.

Main tables:

- `cases`
- `documents`
- `mapping_revisions`
- `jobs`
- `artifacts`
- `deanonymization_sessions`
- `review_decisions`

Interpretation:

- `cases`: top-level desktop workspaces
- `documents`: imported source documents within a case
- `mapping_revisions`: revisioned case-wide mapping state as JSON blobs
- `jobs`: anonymization and deanonymization runs
- `artifacts`: files produced by the system, including anonymized outputs and exports
- `deanonymization_sessions`: pasted deanonymization sessions and their outputs
- `review_decisions`: audit trail for substitution removal actions

Important implementation detail:

- schema migration is done ad hoc inside `bootstrap()` with `ALTER TABLE` checks
- there is no dedicated migration tool such as Alembic

## 8. Core data contracts and invariants

### 8.1 `CanonicalAnonymizationResult`

Defined in `src/models/canonical_result.py`.

This is the rich in-memory result returned by wrappers. It contains:

- anonymized text
- raw backend mapping
- normalized entity replacements
- engine id
- processing metadata
- optional pseudonym metadata

This object is richer than what is persisted to disk.

### 8.2 `MappingArtifact`

Defined in `src/models/mapping_artifact.py`.

This is the persisted cross-layer artifact used for later deanonymization and downstream review/regeneration logic.

Fields:

- `schema_version`
- `mapping_format`
- `origin.engine_id`
- `entries[]`
- optional `integrity_hash`

Each `MappingEntry` contains:

- `placeholder`
- `original_value`
- `entity_type`
- `position_ranges`

Important invariant:

- `mapping_format` must be `canonical-v1`

### 8.3 `BackendDescriptor`

Defined in `src/models/backend_descriptor.py`.

This is the readiness/reporting contract used by CLI and desktop UI:

- `engine_id`
- `display_name`
- `availability_status`
- `capabilities`
- `readiness_checks`

### 8.4 Important contract mismatch to understand

The backend and the persisted mapping are not equivalent.

The transformer backend can produce richer pseudonymization metadata, but `AnonymizationService._to_mapping_artifact()` persists a reduced canonical mapping artifact.

That reduction is safe enough for current deanonymization, but it is one of the most important design tensions in the repo because review/regeneration features need accurate positions and stable replacement semantics.

## 9. Main execution flows

### 9.1 CLI startup flow

File: `src/app/cli/main.py`

Sequence:

1. Ensure runtime dirs.
2. Configure logging.
3. Parse command-line args.
4. Build `ReadinessService`.
5. Cache a startup readiness report.
6. Dispatch the selected handler.
7. Translate uncaught exceptions into one-line user-facing output.

This is the simplest flow and a good debugging surface for core engine issues.

### 9.2 Desktop startup flow

Files:

- `src/app/desktop/main.py`
- `src/app/desktop/window.py`
- `src/services/case_workspace_service.py`

Sequence:

1. Configure logging.
2. Ensure PySide6 is available unless test stubs are active.
3. Build `CaseWorkspaceService()`.
4. Wrap it in `WorkspacePresenter`.
5. Create `DesktopMainWindow`.
6. `window.load()` fetches workspace state and readiness summary.
7. Panels are populated from `WorkspaceLoadViewModel`.

Important architectural note:

- `CaseWorkspaceService()` is effectively the desktop composition root
- it eagerly bootstraps the metadata DB and constructs almost every sub-service itself

### 9.3 Single-file anonymization flow

File: `src/services/anonymization_service.py`

Sequence:

1. Ensure legacy runtime dirs.
2. Resolve wrapper for backend.
3. Enforce readiness.
4. Initialize the wrapper.
5. Load input document via document adapter.
6. Call `wrapper.anonymize(text, options={})`.
7. Save anonymized output.
8. Convert the rich result to a canonical mapping artifact.
9. Save mapping artifact JSON.

Default output locations for the CLI path:

- output: `runtime/outputs/<stem>.<backend>.anon.txt`
- mapping: `runtime/mappings/<stem>.<backend>.mapping.json`

### 9.4 Desktop batch anonymization flow

Primary files:

- `src/services/case_workspace_service.py`
- `src/services/case_batch_service.py`
- `src/adapters/persistence/artifact_store.py`

Sequence:

1. User selects a case and TXT files in the UI.
2. `DesktopMainWindow` submits the work to `WorkspaceWorker`.
3. `CaseWorkspaceService.run_case_anonymization()` delegates to `CaseBatchService`.
4. A `jobs` row is created with a readiness snapshot.
5. Each source file is copied into the case `imports/` directory.
6. Output and mapping paths are allocated under the case folder.
7. `AnonymizationService.run()` is invoked.
8. The generated mapping artifact is merged into the case-wide mapping revision state.
9. The normalized anonymized text and mapping artifact may be rewritten to align with merged case policy.
10. `documents`, `mapping_revisions`, `artifacts`, and `jobs` are updated transactionally.

Important behavior:

- each case has a revisioned, merged mapping state
- per-document outputs are not just stored; they are normalized against the current case policy
- failures are handled per-file, so batch runs can end in `partial`

### 9.5 Mapping review and substitution removal flow

Primary files:

- `src/services/substitution_review_service.py`
- `src/services/mapping_revision_service.py`
- `src/services/stale_state_service.py`

Sequence:

1. Load current document artifact.
2. Verify output integrity and mapping artifact availability.
3. Build review rows from artifact mapping entries plus current case revision state.
4. User selects removable substitutions.
5. Service marks corresponding mapping entries as removed in a new mapping revision.
6. Output text and mapping artifact are rewritten for the current document.
7. A new artifact supersedes the previous one.
8. Other impacted artifacts may become stale.

Critical rule:

- a substitution is only removable if reliable `position_ranges` exist

This rule is safety-oriented and prevents blind textual rewriting.

### 9.6 Stale output regeneration flow

Primary files:

- `src/services/stale_output_regeneration_service.py`
- `src/services/stale_state_service.py`

Sequence:

1. Load an artifact marked stale or lagging behind the current mapping revision.
2. Verify it is the latest artifact for its document.
3. Verify its current output file still matches stored SHA256.
4. Load the original mapping artifact.
5. Determine removed entries since the artifact's revision.
6. Rewrite text and mapping only for affected substitutions.
7. Create a replacement artifact and mark the old one superseded.

Important safeguards:

- regeneration is blocked if the file was edited outside the app
- regeneration is blocked if mapping positions are unreliable
- only the latest artifact for a document can be regenerated

### 9.7 Pasted deanonymization flow

Primary file:

- `src/services/pasted_deanonymization_service.py`

Sequence:

1. Load active mapping entries for the selected case.
2. Build a temporary `MappingArtifact` from active entries.
3. Save pasted input text into the case `sessions/` directory.
4. Run deanonymization in memory.
5. Save the result text in the same session area.
6. Record a `deanonymization_sessions` row and update `jobs`.
7. Optionally export the result to the user-facing exports directory.

Important nuance:

- pasted deanonymization does not require a mapping JSON file on disk from the user
- it rebuilds a compatible mapping artifact from the active case revision

### 9.8 Deanonymization flow

File: `src/services/deanonymization_service.py`

Sequence:

1. Load canonical mapping artifact.
2. Validate compatibility and origin engine support.
3. Enforce readiness for the origin engine.
4. Initialize the wrapper.
5. Load anonymized text.
6. Perform wrapper-level deanonymization.
7. Save restored text.

Important behavior:

- deanonymization is routed by `mapping_artifact.origin.engine_id`, not by a user-selected backend
- the transformer wrapper deanonymizes by deterministic string replacement, not by re-running the model

## 10. Transformer wrapper and backend integration

The transformer wrapper is the key integration point between app code and the backend implementation.

Primary file:

- `src/engines/transformer_wrapper.py`

### 10.1 Dynamic loading

The wrapper uses `importlib.util.spec_from_file_location()` to load:

- `tmp/anonymizer.py`
- `tmp/transformer_anonymizer.py`

This means:

- packaging must ship those files
- import paths are not package-native
- runtime failures can happen if file locations change

### 10.2 Readiness vs wrapper initialization

There are two layers of "is this backend usable?":

- bootstrap readiness checks verify Python modules and model availability
- wrapper initialization verifies the scripts can load and expose the expected callable

Both matter. Passing one does not automatically guarantee the other.

### 10.3 CPU-only enforcement

`TransformerWrapper.anonymize()` forcibly sets:

- `device = -1`

So even if the underlying backend script supports GPU-style options, the application currently forces CPU execution.

### 10.4 Entity normalization and offsets

The wrapper normalizes backend mapping structures into `EntityReplacement` entries, but it currently does not populate trusted offsets from the backend into:

- `start_offset`
- `end_offset`
- `offsets_trusted=True`

That has a major downstream consequence:

- the canonical mapping artifact usually ends up with empty `position_ranges`
- review/removal/regeneration features depend on reliable positions
- therefore some advanced desktop workflows are structurally implemented but constrained by missing positional data

This is one of the most important current weaknesses in the repo.

### 10.5 Deanonymization behavior

The wrapper sorts mapping entries by placeholder length and replaces strings directly.

Properties:

- deterministic
- fast
- local
- easy to test

Risks:

- purely textual replacement can be fragile if replacement tokens overlap in unexpected ways

## 11. Readiness subsystem

Primary files:

- `src/services/readiness_service.py`
- `src/bootstrap/dependency_check.py`
- `src/bootstrap/model_check.py`
- `src/bootstrap/readiness_bootstrap.py`

Readiness is a first-class concern in the repo. Both CLI and desktop surfaces rely on it.

Current transformer readiness checks include:

- `transformers`
- `torch`
- `rapidfuzz`
- `unidecode`
- `gliner`
- `cpu_only_compatibility`
- model availability for `urchade/gliner_multi_pii-v1`

Model lookup sources:

- explicit `ANONYMAPP_TRANSFORMER_MODEL_PATH`
- Hugging Face cache under `HF_HOME`
- default `~/.cache/huggingface`

Status model:

- `ready`
- `degraded`
- `unavailable`

The current transformer backend is blocked only when critical checks fail.

## 12. Packaging and release flow

The repo contains a Linux/WSL-to-Windows staging flow plus the actual Windows build step.

### 12.1 Staging flow

File:

- `scripts/packaging/prepare_windows_test_release.py`

What it does:

1. Run preflight checks on required paths.
2. Collect git metadata.
3. Run targeted regression tests unless skipped.
4. Copy required repo content into `out/windows_test_release/`.
5. Write `build_info.json`, `commit.txt`, and `next_steps_windows.txt`.
6. Verify the staged tree with `verify_staged_release.py`.

### 12.2 Verification flow

File:

- `scripts/packaging/verify_staged_release.py`

What it checks:

- required files/directories exist
- `models/` is present and populated
- build metadata is valid
- portable smoke checks pass

### 12.3 Windows build flow

Files:

- `scripts/packaging/build_windows.ps1`
- `scripts/packaging/a4_desktop.spec`
- `scripts/packaging/build_windows_portable.py`

What happens on Windows:

1. Verify staged layout.
2. Resolve a Python 3.11 interpreter.
3. Create `.venv-windows-build/` if needed.
4. Install build dependencies.
5. Run PyInstaller with the desktop spec.
6. Validate that `dist/a4_desktop_portable/A4Desktop.exe` exists.

Packaging-specific details:

- model assets under `models/` are bundled as data
- desktop assets are bundled as data
- backend scripts under `tmp/` are bundled as data
- several imports are forced through `hiddenimports`
- runtime DLL lookup is Windows/Conda-oriented

## 13. Tests and how to use them

The test suite is broad and mirrors the architecture reasonably well.

### 13.1 Test categories

- `tests/unit/`: narrow service/adapter/model/persistence tests
- `tests/integration/`: higher-level workflow tests across services and persistence
- `tests/ui/`: desktop panel/window tests
- `tests/packaging/`: portable bundle and release staging tests
- `tests/contract/`: explicit contract coverage for engine wrappers

### 13.2 How to choose tests when modifying code

If you change:

- `src/services/*`: run matching unit tests plus relevant integration tests
- `src/app/desktop/*`: run UI tests plus affected service tests
- `src/engines/*` or `tmp/*`: run engine unit tests, contract tests, and anonymization integration tests
- `src/adapters/persistence/*`: run persistence unit tests and affected integration tests
- `scripts/packaging/*`: run packaging tests

### 13.3 Important architectural role of tests

The tests are not just regression checks. They are the clearest executable specification of:

- UI boundaries
- review/edit safety behavior
- stale/regeneration behavior
- portable packaging assumptions

For an LLM, the tests are often a better source of truth than old markdown docs.

## 14. How to run and use the repo

### 14.1 Setup

Typical setup:

```bash
uv sync
```

Alternative:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 14.2 Run the CLI

```bash
python3 -m src.app.cli.main readiness
python3 -m src.app.cli.main anonymize --input /path/to/input.txt
python3 -m src.app.cli.main deanonymize --input /path/to/anonymized.txt --mapping /path/to/mapping.json
```

### 14.3 Run the desktop app

```bash
python3 -m src.app.desktop.main
```

For headless/test-oriented runs:

```bash
ANONYMAPP_FORCE_QT_OFFSCREEN=1 python3 -m src.app.desktop.main
```

### 14.4 Run tests

```bash
python3 -m pytest
python3 -m ruff check .
```

Or a narrower slice:

```bash
python3 -m pytest tests/unit/services/test_mapping_revision_service.py
python3 -m pytest tests/ui/test_desktop_workspace_smoke.py
python3 -m pytest tests/packaging/test_windows_portable_smoke.py
```

### 14.5 Prepare a Windows staged release

```bash
python3 scripts/packaging/prepare_windows_test_release.py
```

Then, on Windows in the staged folder:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/packaging/build_windows.ps1
```

## 15. Architecture hotspots

These files deserve extra care because a change there has wide impact:

- `src/services/case_workspace_service.py`
- `src/services/mapping_revision_service.py`
- `src/services/stale_state_service.py`
- `src/services/substitution_review_service.py`
- `src/engines/transformer_wrapper.py`
- `src/adapters/persistence/database.py`
- `src/adapters/persistence/artifact_store.py`
- `scripts/packaging/build_windows_portable.py`

## 16. Safe modification strategy for a coding LLM

When improving the repo, use this strategy:

1. Decide whether the change is UI-only, service-level, persistence-level, engine-level, or packaging-level.
2. Read the closest tests first.
3. Preserve `ui_contracts` shapes unless the user explicitly wants UI contract changes.
4. Preserve filesystem naming conventions unless you also update packaging/tests.
5. Preserve mapping compatibility unless you are intentionally versioning the artifact format.
6. If you touch `tmp/` or wrapper code, assume packaging and readiness may break.
7. If you touch `database.py`, assume migration and data-compatibility risks.

## 17. Current weaknesses

The repo is solid enough for iterative development, but it has several structural weaknesses.

### 17.1 Dual product shape

There are effectively two apps in one repo:

- a simple CLI/runtime flow
- a richer desktop/case-management flow

They share some services but not the same storage model or user journey. This increases cognitive load and makes architecture docs harder to keep coherent.

### 17.2 Dynamic `tmp/` backend loading

The production transformer implementation is not a normal importable package module. It is loaded from `tmp/` files at runtime.

This is fragile because:

- packaging must manually carry the scripts
- path assumptions matter everywhere
- import behavior is harder to reason about

### 17.3 `CaseWorkspaceService` is a very large composition root/facade

It constructs many repositories and services directly and exposes a broad API surface. This is pragmatic, but it also means:

- high fan-in
- harder isolated refactoring
- many responsibilities meet in one class

### 17.4 Review/regeneration features depend on positional data that is not reliably produced

This is the most important functional weakness today.

- review/removal/regeneration logic requires reliable `position_ranges`
- `TransformerWrapper` does not currently propagate trusted offsets
- as a result, advanced editing workflows may exist in code and tests but be constrained in real usage

### 17.5 Mapping revision storage is JSON-heavy and denormalized

Per-case mapping state is stored as JSON blobs in `mapping_revisions.entries_json`.

That keeps implementation simple, but it weakens:

- queryability
- partial updates
- relational integrity
- long-term migration flexibility

### 17.6 Database migrations are manual

Schema evolution is implemented inline in `MetadataDatabase.bootstrap()`.

This is acceptable for a small local app, but it does not scale well for:

- multiple schema versions
- rollback planning
- auditability
- future external installers/updaters

### 17.7 Qt test stubs are useful but can hide real-widget issues

`qt_compat.py` makes tests easy to run without full PySide6, but some UI tests validate behavior against stub widgets rather than real Qt objects.

This lowers friction, but increases the chance of UI/runtime mismatches.

### 17.8 Packaging is Windows-specific and somewhat environment-sensitive

The portable build flow assumes:

- Windows final build host
- Python 3.11 availability
- PyInstaller behavior
- Conda-style runtime DLL discovery in some scenarios
- local model assets already present

This is workable, but brittle.

### 17.9 Abstractions are ahead of actual product breadth

The codebase contains abstractions for:

- multiple engines
- multiple document formats
- richer review workflows

But the implemented production path is still mostly:

- transformer backend
- TXT documents
- local-only CPU execution

This is not wrong, but it means some abstraction layers are paying complexity costs before the product breadth fully exists.

## 18. Improvement axes

These are the most valuable improvement directions.

### 18.1 Make the backend integration package-native

Move logic from `tmp/` into a normal importable package under `src/`, or at least create a cleaner adapter boundary around it.

Benefits:

- less packaging fragility
- cleaner imports
- easier testability
- more predictable dependency analysis

### 18.2 Define an official canonical mapping v2

If review/regeneration are important, the artifact format should explicitly preserve:

- trusted positions
- stable replacement semantics
- pseudonym metadata needed by downstream workflows

This would remove the current lossy gap between rich backend output and persisted artifacts.

### 18.3 Split desktop composition from desktop behavior

Keep `CaseWorkspaceService` as an app facade if desired, but move object construction into a dedicated composition module or factory.

Benefits:

- easier dependency injection
- easier testing of alternate configurations
- lower class-level complexity

### 18.4 Introduce real database migrations

Adopt a migration strategy, even if lightweight.

Benefits:

- clearer schema evolution
- safer upgrades
- better maintainability

### 18.5 Normalize mapping revision storage

Consider moving mapping entries into a dedicated table or hybrid representation instead of only JSON blobs.

Benefits:

- better queries
- easier conflict analysis
- easier future UI features

### 18.6 Clarify product direction between CLI and desktop

Decide whether the CLI is:

- a supported user surface
- a developer/debug tool
- or a compatibility layer

That decision should drive docs, tests, and storage conventions.

### 18.7 Strengthen real end-to-end desktop and packaging validation

Add more coverage that exercises:

- real PySide6 where possible
- real packaged Windows builds in CI or dedicated release validation
- real model-backed end-to-end flows

### 18.8 Improve model asset management

The repo currently assumes local model availability but does not centralize model provisioning in a robust way.

Possible improvements:

- a dedicated model manager
- explicit download/cache/provision workflows
- clearer docs for packaged vs developer environments

## 19. Where to start depending on the change you want

If you want to:

- change desktop UI behavior: start in `src/app/desktop/window.py`, the relevant widget, and `tests/ui/`
- change case workflow behavior: start in `src/services/case_workspace_service.py` and related service tests
- change anonymization/deanonymization semantics: start in `src/services/anonymization_service.py`, `src/services/deanonymization_service.py`, and `src/engines/transformer_wrapper.py`
- change review or stale artifact logic: start in `src/services/substitution_review_service.py`, `src/services/stale_state_service.py`, and `src/services/stale_output_regeneration_service.py`
- change persistence: start in `src/adapters/persistence/` and `tests/unit/persistence/`
- change portable packaging: start in `scripts/packaging/` and `tests/packaging/`

## 20. Bottom line

The current repo is best understood as:

- a local anonymization engine integration
- wrapped in a growing desktop case-management application
- backed by SQLite metadata plus filesystem artifacts
- with a Windows portable packaging pipeline

Its strongest qualities are:

- clear service-oriented business logic
- strong local-first assumptions
- meaningful tests around safety and workflow behavior
- practical packaging helpers for the target distribution model

Its main weaknesses are:

- dynamic backend loading from `tmp/`
- dual CLI/desktop mental models
- lossy mapping persistence relative to richer backend output
- manual migration and packaging fragility

If you are improving the repo, the best leverage is usually in:

- backend contract cleanup
- mapping artifact evolution
- desktop composition simplification
- stronger end-to-end validation
