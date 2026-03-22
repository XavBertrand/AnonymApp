# AnonymApp Technical Architecture

This document explains how the code works internally and highlights the integration details that matter if you want to build a UI on top of the current implementation.

The document is intentionally implementation-focused. It describes real code paths, real data contracts, runtime behavior, failure modes, and practical UI implications.

## 1. Scope and current product shape

The repository currently implements a local, file-based anonymization tool for plain text documents.

Current scope:

- Input format: `.txt`
- Output format: `.txt`
- Supported anonymization backend: `transformer`
- Supported reversible flow: anonymize a text file, save a canonical mapping artifact, later deanonymize using that mapping
- Execution model: synchronous, local-first, CPU-only in the wrapper

Important limitation:

- The backend itself can support richer options, but the current application layer exposes a minimal subset of them

## 2. High-level architecture

The codebase is split into a few clear layers.

### Entry layer

- `src/app/cli/main.py`

This is the only user-facing entry point in the repository today. It parses CLI arguments, performs startup readiness checks, dispatches commands, and prints short status lines to stdout.

### Service layer

- `src/services/anonymization_service.py`
- `src/services/deanonymization_service.py`
- `src/services/readiness_service.py`

These services orchestrate document I/O, backend selection, readiness enforcement, mapping generation, and output persistence.

### Wrapper layer

- `src/engines/transformer_wrapper.py`
- `src/engines/base.py`

The wrapper abstracts the backend implementation and normalizes its output into application-level data models.

### Data contracts

- `src/models/backend_descriptor.py`
- `src/models/canonical_result.py`
- `src/models/mapping_artifact.py`

These define the shapes that the service layer moves around.

### Adapters

- `src/adapters/documents/txt_adapter.py`
- `src/adapters/mappings/canonical_mapping_adapter.py`

Adapters isolate persistence details for documents and mappings.

### Bootstrap and readiness

- `src/bootstrap/dependency_check.py`
- `src/bootstrap/model_check.py`
- `src/bootstrap/readiness_bootstrap.py`

This subsystem reports whether the backend can be used.

### Bundled backend scripts

- `tmp/transformer_anonymizer.py`
- `tmp/anonymizer.py`

The transformer wrapper dynamically loads these scripts at runtime. The transformer backend depends on symbols imported from `tmp/anonymizer.py`, so both files must exist.

## 3. End-to-end flows

### 3.1 Startup flow

Every CLI invocation goes through this sequence:

1. `ensure_runtime_dirs()` creates `runtime/outputs`, `runtime/mappings`, and `runtime/logs` if they do not exist.
2. `configure_logging()` configures root logging and writes logs to `runtime/logs/anonymapp.log`.
3. The CLI parser reads the command and arguments.
4. `ReadinessService().get_readiness_report(refresh=True)` computes a fresh backend readiness report.
5. The readiness report is attached to the parsed args object.
6. The selected command handler runs.
7. If an exception escapes the handler, it is logged and translated into a user-facing error string.

UI implication:

- A desktop or web UI can safely do the same on application boot: create runtime folders, run readiness, cache the report, then enable or disable actions based on readiness status.

### 3.2 Anonymization flow

The anonymization path is implemented by `run_anonymization_job()` and `AnonymizationService.run()`.

Sequence:

1. The service validates runtime directories.
2. It resolves the wrapper from the backend name.
3. It enforces readiness through `ReadinessService.assert_backend_usable(...)`.
4. It initializes the backend wrapper.
5. It reads the input text file with `TxtDocumentAdapter.load(...)`.
6. It calls `wrapper.anonymize(text, options={})`.
7. It writes the anonymized text to disk.
8. It converts the canonical result into a smaller canonical mapping artifact.
9. It writes the mapping artifact JSON to disk.
10. It returns an `AnonymizationJobResult`.

Returned object:

- `result`: full `CanonicalAnonymizationResult`
- `output_path`: anonymized text path
- `mapping_path`: canonical mapping JSON path

Important UI note:

- The service returns more information in memory than it persists on disk. The saved mapping artifact is intentionally smaller than the in-memory backend mapping.

### 3.3 Deanonymization flow

The deanonymization path is implemented by `run_deanonymization_job()` and `DeanonymizationService.run()`.

Sequence:

1. Runtime directories are ensured.
2. The mapping JSON is loaded and parsed with `CanonicalMappingAdapter.load(...)`.
3. Compatibility checks validate schema version, mapping format, origin metadata, and engine support.
4. The origin backend is taken from `mapping_artifact.origin.engine_id`.
5. Readiness is enforced again for that origin backend.
6. The wrapper is initialized.
7. The adapter validates that the origin backend is not currently unavailable.
8. The anonymized input text is loaded.
9. The wrapper performs deterministic replacement-based deanonymization using the mapping entries.
10. The deanonymized text is written to disk.
11. A `DeanonymizationJobResult` is returned.

Important UI note:

- Deanonymization is routed by the mapping’s origin backend, not by a user-selected backend.

## 4. CLI contract

The current CLI is implemented in `src/app/cli/main.py`.

Supported commands:

- `readiness`
- `anonymize`
- `deanonymize`

### 4.1 `readiness`

Arguments:

- Optional `--backend transformer`

Printed output:

- One block per backend
- Each block contains backend status and per-check lines

Example shape:

```text
[transformer] ready
  - transformers: pass (critical) - available
  - torch: pass (critical) - available
  - gliner: pass (critical) - available
  - urchade/gliner_multi_pii-v1: pass (critical) - model available at ...
```

### 4.2 `anonymize`

Arguments:

- `--input` required
- `--engine transformer` optional, default is `transformer`
- `--output` optional
- `--mapping` optional

Printed output:

```text
Engine: transformer
Anonymized output: /absolute/path/to/output
Mapping artifact: /absolute/path/to/mapping
```

### 4.3 `deanonymize`

Arguments:

- `--input` required
- `--mapping` required
- `--output` optional

Printed output:

```text
Origin engine: transformer
Deanonymized output: /absolute/path/to/output
```

### 4.4 CLI-level error behavior

If a handler raises an exception:

- The exception is logged with stack trace
- A translated one-line message is printed
- The process exits with code `1`

Examples of translated messages:

- `Input file not found. Verify the provided path.`
- `Access denied for file operation. Check file and directory permissions.`
- `Missing runtime dependency. Run readiness checks and install required packages.`
- `Invalid input: ...`

UI implication:

- If a UI shells out to the CLI, stdout/stderr alone are not enough for a rich experience. A direct Python integration with the service layer will be easier to control.

## 5. Readiness subsystem

The readiness subsystem determines whether anonymization or deanonymization should be allowed.

### 5.1 Data model

Backend availability is represented by `BackendDescriptor`.

Fields:

- `engine_id`
- `display_name`
- `availability_status`
- `capabilities`
- `readiness_checks`
- `last_checked_at`

Per-check status is represented by `ReadinessCheckResult`.

Fields:

- `check_name`
- `severity`
- `status`
- `message`
- `remediation`

Availability status values:

- `ready`
- `degraded`
- `unavailable`

Severity values:

- `critical`
- `warning`

Check status values:

- `pass`
- `fail`

### 5.2 How readiness is built

`build_backend_descriptors()` combines:

- Dependency checks from `run_dependency_checks()`
- Model checks from `run_model_checks()`

The only backend currently emitted is:

- `transformer`

### 5.3 Dependency checks

The current required modules are:

- `transformers`
- `torch`
- `rapidfuzz`
- `unidecode`
- `gliner`

There is also a synthetic readiness check:

- `cpu_only_compatibility`

That check always passes and states that CPU-only execution is supported.

### 5.4 Model checks

The current required model is:

- `urchade/gliner_multi_pii-v1`

Model lookup locations:

- `ANONYMAPP_TRANSFORMER_MODEL_PATH`
- Hugging Face cache under `HF_HOME`
- `~/.cache/huggingface` when `HF_HOME` is absent

### 5.5 Enforcement

`ReadinessService.assert_backend_usable(...)` blocks only when `availability_status == "unavailable"`.

If blocked, it raises `ReadinessError` with:

- `engine_id`
- `operation`
- `detail`
- `remediation`

The error message already contains a user-facing explanation.

UI implication:

- A UI can directly show `availability_status` as a badge.
- Use the `readiness_checks` list to populate a diagnostics panel.
- Disable action buttons when status is `unavailable`.
- Keep the remediation string visible and copyable.

## 6. Engine wrapper contract

`EngineWrapper` is defined as a protocol in `src/engines/base.py`.

Methods:

- `initialize(config) -> BackendDescriptor`
- `anonymize(text, options=None) -> CanonicalAnonymizationResult`
- `deanonymize(anonymized_text, mapping_artifact) -> str`
- `readiness_checks() -> list[ReadinessCheckResult]`

The current production wrapper is `TransformerWrapper`.

## 7. Transformer wrapper behavior

`src/engines/transformer_wrapper.py` is the most important runtime integration point.

### 7.1 Dynamic module loading

The wrapper loads Python files directly from disk:

- Transformer script: `tmp/transformer_anonymizer.py`
- Supporting script: `tmp/anonymizer.py`

It uses `importlib.util.spec_from_file_location(...)` and inserts modules into `sys.modules`.

Why this matters:

- UI packaging must ship both scripts.
- If a packaged desktop app changes file locations, the wrapper path configuration must be updated.
- Missing backend scripts surface as readiness failures and runtime errors.

### 7.2 Initialization

`initialize(...)` does not run a full health check of the model.

It verifies:

- The script can be loaded
- The module exposes a callable `run_transformer_anonymization`

It returns a `BackendDescriptor` whose availability is:

- `ready` when those checks pass
- `unavailable` when loading fails

Important nuance:

- Readiness at the wrapper level is not the same as overall application readiness.
- The stronger model and dependency checks happen in the bootstrap layer.

### 7.3 Anonymization call

`wrapper.anonymize(text, options={})` does the following:

1. Ensures the backend module is loaded.
2. Looks up `run_transformer_anonymization`.
3. Copies the options dictionary.
4. Forces `opts["device"] = -1`.
5. Calls `run_transformer_anonymization(text, **opts)`.
6. Ensures `mapping["meta"]["device"] = -1` when the backend returns a dict.
7. Converts the raw mapping to a `CanonicalAnonymizationResult`.
8. Validates the canonical result.

The CPU-only enforcement is hardcoded at wrapper level.

UI implication:

- There is no exposed GPU toggle in the current application layer.
- A UI should present current execution as CPU-only unless the wrapper is changed.

### 7.4 Entity normalization

The wrapper supports two raw backend mapping shapes:

- `mapping["entities"]` as a dict keyed by placeholder
- `mapping["entities"]` as a list of entity objects

It normalizes both shapes into a list of `EntityReplacement`.

Fields in `EntityReplacement`:

- `entity_type`
- `source_value`
- `replacement_value`
- `confidence`
- `start_offset`
- `end_offset`

Current limitation:

- The wrapper does not propagate text offsets from the current backend mapping into `start_offset` and `end_offset`.
- A review UI can show entities and values, but not precise span highlighting from the persisted canonical result alone.

### 7.5 Deanonymization in the wrapper

The wrapper deanonymization logic is intentionally simple.

It sorts mapping entries by placeholder length descending and then does string replacement.

This means:

- Deanonymization does not call the transformer backend
- Deanonymization is deterministic and fast
- UI progress for deanonymization can be very simple

## 8. Bundled transformer backend behavior

The actual anonymization logic lives in `tmp/transformer_anonymizer.py`.

### 8.1 Core behavior

`run_transformer_anonymization(...)` instantiates `TransformerAnonymizer` and returns:

- `anonymized_text`
- `mapping`

Default parameters:

- `model_name="urchade/gliner_multi_pii-v1"`
- `device="cuda"` at script API level, but the wrapper overrides it to `-1`
- `preserve_dates=True`

### 8.2 Detection pipeline

The transformer backend merges several sources of detection:

- GLiNER predictions when the model name contains `"gliner"`
- Optional domain entities
- Pattern-based entities
- Structured entities such as email, phone, IBAN, SIREN/SIRET, URL, and dates

It then deduplicates and normalizes them.

### 8.3 Pseudonym strategy

The backend does not simply replace entities with placeholders inside the text.

It generates realistic deterministic pseudonyms for categories such as:

- `PERSON`
- `ORGANIZATION`
- `LOCATION`
- `PHONE`
- `EMAIL`
- `IBAN`
- `DATE`
- `URL`

The text output therefore contains pseudonyms, while the internal mapping still tracks placeholder tags such as `<PERSON_1>`.

This is a critical point for UI design:

- The user-visible anonymized text is pseudonymized
- The persisted mapping artifact does not retain the full rich pseudonymization structure
- The current wrapper-to-artifact conversion should be treated as a contract risk and validated against real backend output

### 8.4 Raw backend mapping structure

The raw mapping returned by `tmp/transformer_anonymizer.py` can contain fields like:

```json
{
  "entities": {
    "<PERSON_1>": {
      "label": "PERSON",
      "values": ["Alice Martin"],
      "variants": ["Alice", "Alice Martin"],
      "source": "gliner",
      "score": 0.91,
      "canonical": "Alice Martin",
      "pseudonym": "Camille Dupont"
    }
  },
  "reverse_map": {
    "<PERSON_1>": "Alice Martin"
  },
  "pseudonym_map": {
    "<PERSON_1>": "Camille Dupont"
  },
  "pseudonym_reverse_map": {
    "Camille Dupont": "Alice Martin"
  },
  "stats": {
    "total": 3,
    "by_type": {
      "PERSON": 1
    }
  },
  "corrected_text": "Alice Martin called...",
  "placeholder_style": "pseudonym",
  "meta": {
    "device": -1
  }
}
```

Important distinction:

- This rich raw mapping is returned in memory as part of `CanonicalAnonymizationResult.mapping`
- It is not what gets written as the canonical mapping artifact JSON used for later deanonymization

### 8.5 Backend-specific heuristics

The transformer backend includes substantial text heuristics:

- Fuzzy grouping of similar entity surfaces with `rapidfuzz`
- Canonical surface selection
- Case normalization
- Lowercase false-positive filtering
- Preservation of speaker labels like `SPEAKER_1:`
- Date preservation logic

UI implication:

- The backend is not a pure ML black box. It is a hybrid ML-plus-rules anonymizer.
- If a UI later exposes “advanced settings”, many useful candidates already exist in the backend, but they are not exposed by the current service layer.

## 9. Canonical result model

The service layer standardizes anonymization output through `CanonicalAnonymizationResult`.

Fields:

- `anonymized_text`
- `mapping`
- `entities`
- `engine_id`
- `processing_metadata`
- `pseudonym_metadata`

`processing_metadata` contains:

- `request_id`
- `duration_ms`
- `local_only_mode`
- `warnings`
- `optional_services_used`
- `created_at`

Current behavior:

- `local_only_mode` is always `True`
- `warnings` is currently not populated by the transformer wrapper
- `optional_services_used` is currently not populated by the transformer wrapper
- `pseudonym_metadata` is copied from `mapping.get("pseudonym_map")`

UI implication:

- If the UI calls the service layer directly, it can show timing, request ID, entity list, and pseudonym metadata immediately after anonymization.
- If the UI later reloads only the saved mapping file from disk, most of that detail is gone.

## 10. Canonical mapping artifact

The canonical mapping artifact is the only persisted structure used for reversible deanonymization.

### 10.1 Shape

The saved JSON shape is:

```json
{
  "schema_version": "1.0",
  "mapping_format": "canonical-v1",
  "origin": {
    "engine_id": "transformer",
    "generated_at": "2026-03-22T10:00:00+00:00",
    "wrapper_contract_version": "1.0"
  },
  "entries": [
    {
      "placeholder": "Camille Dupont",
      "original_value": "Alice Martin",
      "entity_type": "PERSON",
      "position_ranges": []
    }
  ],
  "integrity_hash": null
}
```

Important nuance:

- The field is named `placeholder`, but in the current transformer flow it actually receives `result.entities[*].replacement_value`
- In the current transformer wrapper implementation, `replacement_value` is derived from the raw mapping key when `mapping["entities"]` is a dict
- For the bundled backend, that raw mapping key is typically a tag such as `<PERSON_1>`, while the anonymized text itself contains the generated pseudonym string

This creates a likely contract mismatch:

- The saved mapping artifact may contain `<PERSON_1> -> Alice Martin`
- The anonymized text may contain `Camille Dupont`
- The current deanonymization logic replaces persisted `placeholder` values in the text
- If the text contains pseudonyms rather than tags, no replacement occurs

This is important enough to state explicitly:

- The current deanonymization contract should be validated against a real transformer anonymization output before a UI promises round-trip restoration as a guaranteed user feature
- The existing round-trip tests use simplified stub backends that emit placeholder-like replacements, so they do not prove that the real pseudonymizing backend round-trips correctly today

This naming mismatch is important for UI and future API evolution:

- The persisted artifact is semantically “replacement token or replacement string” rather than a strict placeholder-only format

### 10.2 How artifacts are generated

`AnonymizationService._to_mapping_artifact(...)` iterates over `result.entities` and stores:

- `replacement_value` as `placeholder`
- `source_value` as `original_value`
- `entity_type`

What is not persisted:

- Confidence scores
- Variants
- Corrected text
- Pseudonym reverse map
- Backend stats
- Processing metadata

UI implication:

- If you want an entity review screen after anonymization, render it immediately from `CanonicalAnonymizationResult`.
- If you want that screen to remain available after application restart, you need an additional persisted artifact beyond the current canonical mapping file.
- If you want reliable transformer round-tripping, you should also verify or revise how replacement values are persisted.

## 11. Mapping adapter and compatibility rules

`CanonicalMappingAdapter` is strict and UI-friendly.

It validates:

- JSON parseability
- Presence of `schema_version`
- Presence of `mapping_format`
- Presence of `origin`
- Presence of `origin.engine_id`
- Presence of `origin.generated_at`
- Presence of `origin.wrapper_contract_version`
- Entry shape and required fields
- Supported schema version
- Supported mapping format
- Supported wrapper contract version
- Supported backend IDs when requested

The adapter raises `MappingCompatibilityError` with:

- `category`
- `detail`
- `remediation`

Current categories include:

- `unsupported_schema_version`
- `unknown_engine_id`
- `missing_required_metadata`
- `unsupported_mapping_format`
- `origin_backend_unavailable`
- `invalid_mapping_file`

UI implication:

- These categories are structured enough to drive targeted dialogs and remediation banners.
- A mapping import screen should display both the category and remediation.

## 12. Runtime paths and file lifecycle

Runtime paths come from `src/config/settings.py`.

Directories:

- `runtime/outputs`
- `runtime/mappings`
- `runtime/logs`

Bundled script paths:

- `tmp/anonymizer.py`
- `tmp/transformer_anonymizer.py`

Default anonymization filenames:

- Output: `<input_stem>.transformer.anon.txt`
- Mapping: `<input_stem>.transformer.mapping.json`

Default deanonymization filename:

- `<deanonymize_input_stem>.<origin_backend>.deanon.txt`

Important nuance:

- If the user deanonymizes `sample.transformer.anon.txt`, the default output becomes `sample.transformer.anon.transformer.deanon.txt`

UI implication:

- A UI should probably propose friendlier save names than the raw default.
- It is worth letting the user choose output locations explicitly.

## 13. Logging and observability

Logging is intentionally simple.

Behavior:

- Root logger is configured once
- Logs go to `runtime/logs/anonymapp.log`
- Logs also go to stderr/console via `StreamHandler`
- Exceptions are logged with stack trace

UI implication:

- A desktop UI could expose a “View logs” action pointing to `runtime/logs/anonymapp.log`
- The current code does not expose structured progress events, percent completion, or job IDs beyond the request ID stored in `processing_metadata`

## 14. Failure modes that matter for UI

These are the most important practical failures to anticipate.

### Missing input file

Source:

- `TxtDocumentAdapter.load(...)`

User-facing effect:

- `FileNotFoundError`
- translated to a short readable message

### Mapping file invalid or incompatible

Source:

- `CanonicalMappingAdapter.load(...)`
- `CanonicalMappingAdapter.validate_compatibility(...)`

User-facing effect:

- `MappingCompatibilityError` with category and remediation

### Backend unavailable

Source:

- `ReadinessService.assert_backend_usable(...)`

User-facing effect:

- `ReadinessError` including failed checks and remediation hints

### Missing backend scripts

Source:

- `TransformerWrapper._load_module(...)`

User-facing effect:

- Readiness failure or runtime failure

### Missing Python dependencies

Source:

- dependency checks
- dynamic module import inside wrapper/backend

User-facing effect:

- readiness can report missing packages before the action runs

### Missing model assets

Source:

- model checks

User-facing effect:

- backend becomes unavailable and actions are blocked

## 15. What the UI should integrate directly

If you want the most capable UI, prefer calling the Python services directly instead of shelling out to the CLI.

Best integration points:

- `ReadinessService.get_readiness_report()`
- `AnonymizationService.run(...)`
- `DeanonymizationService.run(...)`

Why this is better:

- You get typed Python objects instead of parsing stdout
- You retain full `CanonicalAnonymizationResult` in memory
- You can access entity lists, timing, and raw backend mapping immediately
- You can control error rendering based on exception type

## 16. Recommended UI model

Given the current code, an effective UI would likely have these views and behaviors.

### Startup diagnostics

Show:

- Backend card for `transformer`
- Overall readiness badge
- Per-check list with pass/fail state
- Remediation text
- Model path hints

### Anonymization screen

Inputs:

- Source text file
- Optional output path
- Optional mapping path

Display after run:

- Anonymized text preview
- Output file path
- Mapping file path
- Execution duration
- Entity table from `result.entities`
- Pseudonym map from `result.pseudonym_metadata`

### Deanonymization screen

Inputs:

- Anonymized text file
- Mapping artifact file
- Optional output path

Display after run:

- Restored text preview
- Output file path
- Origin engine from `mapping.origin.engine_id`

### Error handling

The UI should distinguish:

- Readiness errors
- Mapping compatibility errors
- File errors
- Unexpected runtime errors

### Progress handling

The current code is synchronous and does not emit progress events.

Recommended UX:

- Use an indeterminate spinner during anonymization
- Show a cancel button only if the UI runs the job in a worker thread or subprocess
- Disable action buttons while a job is running

## 17. Gaps between current backend capability and app capability

The bundled backend can accept richer inputs than the service layer currently sends.

Backend parameters supported by `run_transformer_anonymization(...)`:

- `text`
- `domain_entities`
- `preserve_dates`
- `model_name`
- `device`

Current service/wrapper usage:

- `text` is passed
- `device` is forcibly overwritten to `-1`
- `domain_entities` is not exposed
- `preserve_dates` is not exposed
- `model_name` is not exposed

UI implication:

- If you plan an “advanced settings” panel, the backend can already support more options than the current application API exposes.
- Adding those options cleanly would require service and CLI changes, not just UI work.

## 18. Summary for UI builders

The most important technical truths are:

- The app is local, synchronous, file-based, and currently centered on `.txt` documents.
- Readiness is a first-class concept and should be surfaced prominently.
- The transformer wrapper forces CPU-only execution.
- The rich anonymization result exists only in memory unless you persist something additional.
- The saved canonical mapping artifact is intentionally minimal and optimized for reliable deanonymization, not rich review.
- There is a current contract risk between pseudonymized transformer output and the persisted replacement values used for deanonymization.
- Deanonymization is deterministic string replacement driven by the mapping artifact’s origin backend.
- The cleanest UI integration is through the service layer, not through stdout parsing.
