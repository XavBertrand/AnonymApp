# Desktop Workspace Contract

This contract defines the desktop-facing application operations that the Qt UI must consume. The desktop layer remains a local client of the existing Python service layer and related case-workspace orchestration services.

## 1. Workspace Load

- **Operation**: `load_workspace()`
- **Purpose**: Initialize the main window with readiness, case history, and last-opened selection context.
- **Returns**:
  - readiness summary
  - case list for the left history panel
  - selected case details if a case should reopen automatically
- **Failure Behavior**:
  - If readiness cannot be evaluated, return a blocked or degraded state with actionable diagnostics instead of failing silently.

## 2. Create Case

- **Operation**: `create_case(display_name)`
- **Purpose**: Create a new durable legal-matter workspace.
- **Input Rules**:
  - Display name is required.
- **Returns**:
  - new case identifier
  - initial case status summary
  - empty file/output history

## 3. Open Case

- **Operation**: `open_case(case_id)`
- **Purpose**: Load all user-visible state for an existing case.
- **Returns**:
  - case metadata
  - case status summary
  - active mapping revision summary
  - file list with statuses and preview snippets
  - output artifacts with freshness state
  - recent job history

## 4. Start Batch Anonymization

- **Operation**: `run_case_anonymization(case_id, txt_file_paths[])`
- **Purpose**: Process one or more TXT files sequentially under the active case mapping.
- **Input Rules**:
  - At least one TXT file path is required.
  - Files are processed sequentially in the order supplied.
- **Processing Rules**:
  - The existing anonymization service remains the processing authority.
  - The case mapping is merged deterministically.
  - Per-file failure does not abort the whole batch.
- **Returns**:
  - batch job record
  - per-file statuses
  - generated artifacts
  - updated case status summary
  - updated mapping revision summary when the mapping changed

## 5. Load Substitution Review

- **Operation**: `load_substitution_review(case_id, document_id)`
- **Purpose**: Show reviewable original-to-replacement pairs and the current generated preview for one processed document.
- **Returns**:
  - current output preview
  - substitution rows
  - mapping revision used
  - stale/current state

## 6. Apply Substitution Removal

- **Operation**: `remove_substitutions(case_id, document_id, mapping_entry_ids[])`
- **Purpose**: Remove one or more substitutions from the active case mapping and regenerate the relevant preview.
- **Input Rules**:
  - Only existing substitutions may be removed.
  - MVP does not allow arbitrary substitution creation.
- **Processing Rules**:
  - Removal creates a new mapping revision or equivalent tracked change.
  - Affected prior outputs are marked stale.
  - The newly regenerated preview reflects the updated mapping state.
- **Returns**:
  - updated mapping revision summary
  - regenerated preview
  - impacted output list
  - updated case status summary

## 7. Paste Deanonymization

- **Operation**: `deanonymize_pasted_text(case_id, input_text)`
- **Purpose**: Deanonymize new anonymized text using the active case mapping.
- **Processing Rules**:
  - Known matches are restored.
  - Unknown content remains unchanged.
  - Zero matches return unchanged text with a no-match result state.
- **Returns**:
  - result text
  - match count
  - result state (`matched`, `partial`, `no_match`, `failed`)
  - mapping revision used

## 8. Export Deanonymized Result

- **Operation**: `export_deanonymized_result(case_id, session_id, optional_destination)`
- **Purpose**: Persist the result of a pasted deanonymization session with a friendly default filename.
- **Returns**:
  - output artifact record
  - final file path

## 9. Delete Case

- **Operation**: `delete_case(case_id, confirmed)`
- **Purpose**: Remove a case from active user history after explicit confirmation.
- **Input Rules**:
  - Deletion requires positive confirmation from the user.
- **Returns**:
  - deletion success state
  - updated case history list

## 10. Readiness Detail

- **Operation**: `get_readiness_details()`
- **Purpose**: Provide expanded diagnostics behind the simplified readiness indicator.
- **Returns**:
  - backend readiness state
  - per-check pass/fail details
  - remediation guidance
