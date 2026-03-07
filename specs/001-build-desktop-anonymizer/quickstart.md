# Quickstart: Windows Desktop Anonymization MVP

## Goal
Validate the MVP workflow end-to-end with both existing anonymization engines,
canonical result normalization, mapping export/import, and deanonymization.

## Prerequisites
- Feature branch: `001-build-desktop-anonymizer`
- Local repository with `tmp/anonymizer.py` and `tmp/transformer_anonymizer.py`
- Windows-targeted runtime artifacts prepared by project setup tasks

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
