# Data Model: A4 Desktop Case Workspace

## 1. Case

- **Purpose**: Durable workspace representing one legal matter.
- **Key Fields**:
  - `case_id`
  - `display_name`
  - `created_at`
  - `updated_at`
  - `last_opened_at`
  - `status_summary`
  - `active_mapping_revision`
  - `current_readiness_state`
  - `deleted_at` (nullable, if soft-delete is used internally)
- **Relationships**:
  - Has many `CaseDocument`
  - Has many `JobRecord`
  - Has many `MappingRevision`
  - Has many `OutputArtifact`
  - Has many `DeanonymizationSession`
- **Validation Rules**:
  - Display name is required and human-readable.
  - Active mapping revision must reference an existing mapping revision when any mapping exists.
  - Deleted cases must not appear in the standard history list.
- **Derived/Computed Values**:
  - `status_summary` can be derived from readiness, failed jobs, and stale outputs.

## 2. Case Status Summary

- **Purpose**: Simplified health signal shown in the main window for the selected case.
- **Allowed States**:
  - `ready`
  - `partial`
  - `error`
  - `stale`
  - `blocked`
- **State Meaning**:
  - `ready`: latest readiness is usable and no known stale outputs or unresolved failures need attention.
  - `partial`: some files or jobs failed, but the case remains usable.
  - `error`: the latest critical operation failed in a way that blocks intended work for that item.
  - `stale`: one or more current case outputs no longer match the active mapping revision.
  - `blocked`: readiness prevents anonymization/deanonymization because required local assets are unavailable.

## 3. Mapping Revision

- **Purpose**: Versioned record of the active case mapping over time.
- **Key Fields**:
  - `case_id`
  - `revision_number`
  - `created_at`
  - `change_reason`
  - `base_revision_number` (nullable for the first revision)
  - `entry_count`
  - `conflict_resolution_strategy`
  - `created_by_action`
- **Relationships**:
  - Belongs to one `Case`
  - Has many `MappingEntry`
  - Is referenced by many `OutputArtifact`
  - Is referenced by many `JobRecord`
  - Is referenced by many `DeanonymizationSession`
- **Validation Rules**:
  - Revision number must be monotonic within a case.
  - Every revision after the first must reference a prior base revision or equivalent change lineage.
  - Change reason must explain whether the revision came from batch merge, substitution removal, regeneration, or another supported workflow.

## 4. Mapping Entry

- **Purpose**: One active or removed substitution tracked within a case mapping.
- **Key Fields**:
  - `mapping_entry_id`
  - `case_id`
  - `canonical_original_value`
  - `stable_pseudonym`
  - `entity_type`
  - `state`
  - `introduced_in_revision`
  - `removed_in_revision` (nullable)
  - `conflict_source`
  - `last_used_at`
- **Relationships**:
  - Belongs to one `Case`
  - Belongs to one or more `MappingRevision` snapshots
  - May be linked to many `OutputArtifact` dependency records
- **Validation Rules**:
  - A given original entity may have only one active pseudonym inside a case.
  - Active entries must not conflict with another active entry for the same canonical original value.
  - Removed entries must preserve enough lineage for stale-output detection and audit.
- **State Values**:
  - `active`
  - `removed`

## 5. Case Document

- **Purpose**: Source TXT file associated with a case.
- **Key Fields**:
  - `document_id`
  - `case_id`
  - `source_filename`
  - `source_display_path`
  - `imported_copy_path` (if the app stores a managed copy)
  - `source_fingerprint`
  - `preview_snippet`
  - `imported_at`
  - `last_processed_at`
  - `document_status`
  - `last_error_summary`
  - `latest_output_artifact_id` (nullable)
- **Relationships**:
  - Belongs to one `Case`
  - Participates in many `JobRecord` items
  - Has many `OutputArtifact`
- **Validation Rules**:
  - TXT is the only supported source type in MVP.
  - Preview snippet should be large enough for identification but should not expose more sensitive data than needed.
  - Source fingerprint should remain stable for duplicate detection and change tracking.
- **State Values**:
  - `new`
  - `queued`
  - `processing`
  - `success`
  - `failed`
  - `stale`

## 6. Job Record

- **Purpose**: Durable record of a user-triggered operation within a case.
- **Key Fields**:
  - `job_id`
  - `case_id`
  - `job_type`
  - `started_at`
  - `completed_at`
  - `job_status`
  - `mapping_revision_used`
  - `item_count`
  - `success_count`
  - `failure_count`
  - `error_summary`
  - `readiness_snapshot`
- **Relationships**:
  - Belongs to one `Case`
  - May reference many `CaseDocument`
  - May create many `OutputArtifact`
- **Validation Rules**:
  - Job status must reflect aggregate item outcomes for batch runs.
  - Each job that uses mapping state must record the revision used.
- **State Values**:
  - `queued`
  - `running`
  - `success`
  - `partial`
  - `failed`
  - `blocked`

## 7. Output Artifact

- **Purpose**: Saved result file or artifact reference created by anonymization, mapping export, or deanonymization export.
- **Key Fields**:
  - `artifact_id`
  - `case_id`
  - `document_id` (nullable for pasted deanonymization exports)
  - `artifact_type`
  - `display_name`
  - `file_path`
  - `created_at`
  - `mapping_revision_used`
  - `artifact_status`
  - `stale_reason` (nullable)
  - `supersedes_artifact_id` (nullable)
  - `preview_snippet`
- **Relationships**:
  - Belongs to one `Case`
  - May belong to one `CaseDocument`
  - Is created by one `JobRecord` or `DeanonymizationSession`
- **Validation Rules**:
  - Artifact records must retain the mapping revision used when created.
  - Stale artifacts must retain their original path and auditability even if regenerated replacements are later created.
- **State Values**:
  - `current`
  - `stale`
  - `missing`
  - `superseded`

## 8. Deanonymization Session

- **Purpose**: Record of pasted-text deanonymization performed inside a case.
- **Key Fields**:
  - `session_id`
  - `case_id`
  - `created_at`
  - `mapping_revision_used`
  - `input_preview_snippet`
  - `result_preview_snippet`
  - `match_count`
  - `session_status`
  - `exported_artifact_id` (nullable)
- **Relationships**:
  - Belongs to one `Case`
  - May create one `OutputArtifact`
- **Validation Rules**:
  - If `match_count` is zero, result text equals the input text and the session status is not treated as a system failure.
- **State Values**:
  - `matched`
  - `partial`
  - `no_match`
  - `failed`

## 9. Review Decision

- **Purpose**: Durable user action that alters the active case substitution set.
- **Key Fields**:
  - `review_decision_id`
  - `case_id`
  - `mapping_entry_id`
  - `decision_type`
  - `decided_at`
  - `applied_in_revision`
  - `affected_artifact_count`
  - `decision_note` (optional)
- **Relationships**:
  - Belongs to one `Case`
  - References one `MappingEntry`
  - Produces one `MappingRevision`
- **Validation Rules**:
  - MVP only supports removal decisions, not arbitrary user-created substitutions.
  - Applying a removal decision must create a new mapping revision or equivalent tracked change.

## 10. Relationship Summary

- One `Case` has many `CaseDocument`, `JobRecord`, `MappingRevision`, `OutputArtifact`, and `DeanonymizationSession`.
- One `MappingRevision` contains many `MappingEntry` records as of that revision.
- One `OutputArtifact` always references the mapping revision used at generation time.
- One `ReviewDecision` creates a new mapping revision and may cause many `OutputArtifact` records to become stale.

## 11. Critical State Transitions

### Mapping entry lifecycle

- `active` → `removed` when the user removes a substitution in review.
- Removed entries are not silently deleted from historical tracking.

### Document lifecycle

- `new` → `queued` → `processing` → `success|failed`
- `success` → `stale` when a later mapping revision invalidates the output tied to that document.

### Artifact lifecycle

- `current` → `stale` when the active case mapping changes and the artifact depended on an affected substitution.
- `current|stale` → `missing` if the saved file no longer exists.
- `current|stale` → `superseded` when a newer replacement artifact is generated and retained.

### Case lifecycle

- `ready|partial|error` ↔ `blocked` depending on readiness state.
- Any case with one or more impacted artifacts may surface `stale` in its case-level status summary.
