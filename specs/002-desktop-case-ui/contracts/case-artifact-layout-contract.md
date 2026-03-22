# Case Artifact Layout Contract

This contract defines the durable storage intent for the desktop workspace so that persistence, packaging, and user-visible artifact discovery stay consistent.

## 1. Storage Domains

The desktop product separates three storage domains:

- **Application metadata**: internal metadata, indexes, and durable case records
- **Case-managed working data**: app-managed copies, mapping snapshots, and supporting files needed to reopen cases safely
- **User-facing exported artifacts**: files a user is expected to find, open, or share

## 2. Required Separation

- Application metadata must not be mixed arbitrarily with exported user files.
- Exported files must remain discoverable through the UI without requiring the user to inspect metadata stores.
- Working data may be app-managed and less user-facing, but it must remain traceable back to its case and source document.

## 3. Artifact Naming Expectations

- Output filenames must be user-friendly and stable enough for legal workflows.
- Generated names should reflect case context and artifact purpose rather than raw technical identifiers alone.
- When a new artifact supersedes a stale artifact, the system must preserve both traceability and user-visible freshness state.

## 4. Mapping Version Linkage

Every saved output artifact record must retain:

- the case identifier
- the generating operation/job
- the mapping revision used at generation time
- the freshness state relative to the latest case mapping

## 5. Missing Artifact Handling

If a previously tracked artifact file is no longer present:

- the case remains reopenable
- the missing artifact is surfaced as missing, not silently discarded
- related metadata and history remain available for audit and troubleshooting

## 6. Portable Model Layout

The portable application distribution must treat packaged models as application assets resolved relative to the extracted application root.

Readiness must fail clearly when packaged model content is:

- missing
- incomplete
- corrupted

## 7. Privacy-Oriented Metadata Handling

- Preview snippets should be limited to what is necessary for user identification.
- Logs and metadata should avoid unnecessary duplication of sensitive source text.
- Internal metadata should favor references, snippets, and derived state over wholesale duplication of original user content whenever feasible.
