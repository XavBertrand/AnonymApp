# Quickstart: Windows Desktop Anonymization MVP

## Goal
Validate the MVP workflow end-to-end with both existing anonymization engines,
canonical result normalization, mapping export/import, and deanonymization.

## Prerequisites
- Feature branch: `001-build-desktop-anonymizer`
- Local repository with `tmp/anonymizer.py` and `tmp/transformer_anonymizer.py`
- Windows-targeted runtime artifacts prepared by project setup tasks

## Windows-first Bootstrap Expectations

- On first launch, run readiness bootstrap before accepting anonymization jobs.
- Readiness report must include per-backend status (`ready`, `degraded`,
  `unavailable`) and remediation steps in plain language.
- Missing optional Ollama/`requests` path must not block core anonymization.
- Missing required backend dependencies or model assets must block only the
  impacted backend, not the entire application if another backend is ready.

## Future Windows Packaging Requirements (Design Only)

- Target a self-contained Windows distribution where end users are not required
  to install Python or manually manage dependencies.
- Distribution assumptions:
  - End users install and launch via Windows-native installer/packaged app flow.
  - Runtime dependencies and backend model prerequisites are validated through
    in-app readiness/bootstrap checks.
- Packaging constraints for future implementation:
  - Preserve local-first execution and CPU-only behavior.
  - Preserve thin-wrapper integration with `tmp` source scripts.
  - Avoid introducing cloud/runtime external requirements for core workflows.
  - Keep packaging work separate from MVP functional scope (TXT anonymization,
    mapping export/import, deanonymization).

## Scenario 1: Backend A TXT anonymization
1. Start application entrypoint (MVP UI/CLI layer).
2. Run backend readiness check.
3. Select local TXT input file.
4. Select backend `classic`.
5. Run anonymization.
6. Verify canonical output preview is shown.
7. Export anonymized TXT and canonical mapping file.

Expected result:
- Operation succeeds without command-line dependency management by end user.
- Output includes canonical mapping metadata with origin engine id.

## Scenario 2: Backend B TXT anonymization
1. Repeat Scenario 1 with backend `transformer`.

Expected result:
- Same UI flow works unchanged.
- Output is canonical and backend-agnostic above engine layer.

## Scenario 3: Mapping-based deanonymization
1. Load anonymized TXT and canonical mapping file from prior run.
2. Trigger deanonymization.

Expected result:
- Compatibility validation passes and routes to origin backend wrapper.
- Original text is restored and exportable.

## Scenario 4: Incompatible mapping handling
1. Load mapping with unsupported schema version or mismatched origin metadata.
2. Trigger deanonymization.

Expected result:
- Operation is blocked with actionable error guidance.
- No partial deanonymized output is produced.

## Scenario 5: Missing dependency readiness behavior
1. Simulate missing dependency/model for one backend.
2. Start app or trigger readiness check.

Expected result:
- Backend status shown as `degraded` or `unavailable` with remediation.
- Other ready backend remains usable.

## Scenario 6: First-launch readiness gate (Windows)
1. Start the application on a fresh Windows environment.
2. Trigger first-launch bootstrap validation.
3. Inspect readiness output for backend dependency/model checks and optional
   service checks.

Expected result:
- Clear readiness summary shown before normal command execution.
- User receives concrete remediation instructions for each failed check.
- Core workflow remains available when at least one backend is ready.
