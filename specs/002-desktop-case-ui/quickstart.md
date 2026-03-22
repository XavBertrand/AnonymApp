# Quickstart: A4 Desktop Case Workspace

## Goal

Validate the planned desktop case workflow end to end while preserving the existing CLI and service behavior.

## Prerequisites

- Python 3.11 environment for the repository
- Required local anonymization dependencies installed
- Local packaged or development model assets available
- Existing repository tests still runnable

## 1. Launch the desktop workspace in development mode

1. Start the desktop application from the repository environment.
2. Confirm the main window opens with:
   - left-side case history
   - central case workspace
   - substitution review area
   - pasted deanonymization area
   - readiness summary

## 2. Create and use a case

1. Create a case named `Dossier Test`.
2. Import two TXT files related to the same legal matter.
3. Run anonymization.
4. Verify:
   - files are processed sequentially
   - per-file statuses are visible
   - outputs are saved automatically
   - the case mapping is shared across both files

## 3. Validate deterministic shared mapping

1. Confirm that the same original entity appearing across both files resolves to one stable pseudonym within the case.
2. If the second file would have produced a conflicting pseudonym, confirm the case keeps the already established mapping and records the batch result without silent drift.

## 4. Review and remove substitutions

1. Open substitution review for one processed file.
2. Remove one substitution.
3. Confirm:
   - the preview is regenerated
   - the case mapping revision increments
   - affected prior outputs are marked stale
   - the UI clearly shows impacted outputs and their stale state

## 5. Reopen the case later

1. Close the application.
2. Reopen it.
3. Open `Dossier Test` from the left-side history.
4. Confirm:
   - files, outputs, statuses, and snippets are still visible
   - the stale/current state is preserved
   - the active mapping revision is preserved

## 6. Deanonymize pasted text

1. Paste anonymized text containing known case substitutions.
2. Run deanonymization.
3. Confirm the restored text appears in-app and can be exported.
4. Paste a second text with no known case substitutions.
5. Confirm the result is unchanged and the UI reports that no matches were applied.

## 7. Regression and packaging checks

1. Run the existing CLI regression suite and confirm current CLI behavior is unchanged.
2. Build the portable Windows distribution.
3. Launch the packaged executable from an extracted folder with no network access.
4. Confirm readiness succeeds using packaged local models and at least one TXT anonymization run completes.
