<!--
Sync Impact Report
- Version change: N/A -> 1.0.0
- Modified principles:
  - N/A -> I. Engine Reuse First
  - N/A -> II. Clear Layered Architecture
  - N/A -> III. Stable Engine Interface
  - N/A -> IV. Incremental Development
  - N/A -> V. Local-First and Privacy
  - N/A -> VI. Deterministic and Auditable Outputs
  - N/A -> VII. Robust Error Handling
  - N/A -> VIII. Testability
  - N/A -> IX. Extensibility
  - N/A -> X. Minimal Invasive Changes
- Added sections:
  - System Boundaries and Non-Goals
  - Development Workflow and Quality Gates
- Removed sections:
  - None
- Templates requiring updates:
  - ✅ updated: .specify/templates/plan-template.md
  - ✅ updated: .specify/templates/spec-template.md
  - ✅ updated: .specify/templates/tasks-template.md
  - ⚠ pending: .specify/templates/commands/*.md (directory not present in repository)
- Follow-up TODOs:
  - None
-->
# AnonymApp Constitution

## Core Principles

### I. Engine Reuse First
Existing anonymization engines are the primary source of anonymization behavior.
New features MUST integrate existing engines through wrappers, adapters, or
facades. Rewriting stable engine internals is prohibited unless a documented
technical blocker proves reuse cannot satisfy the requirement.

Rationale: Preserve validated behavior, reduce regression risk, and accelerate delivery.

### II. Clear Layered Architecture
The system MUST enforce the following layers with explicit boundaries:
UI layer, application/service layer, engine abstraction layer, document adapter
layer, and storage/config layer. Cross-layer calls MUST go only through the
defined adjacent interfaces; bypassing layers is prohibited.

Rationale: Enforced separation keeps the codebase maintainable and testable.

### III. Stable Engine Interface
All anonymization engines MUST implement a common, versioned interface contract.
UI and application logic MUST depend only on this interface, never on concrete
engine internals. Any interface change MUST include backward-compatibility
analysis and migration notes.

Rationale: Backend-agnostic integration enables safe engine evolution.

### IV. Incremental Development
Every feature MUST be delivered in independently functional increments. Each
increment MUST keep the application runnable and MUST not break previously
accepted behavior. Large multi-step rewrites without intermediate working states
are prohibited.

Rationale: Incremental delivery lowers risk and improves feedback cycles.

### V. Local-First and Privacy
Core anonymization workflows MUST run fully locally without mandatory cloud
services. External services (for example optional quality-control backends) MAY
be supported only as opt-in enhancements and MUST fail safely without blocking
local operation.

Rationale: Privacy and deployability are core product requirements.

### VI. Deterministic and Auditable Outputs
Anonymization outputs MUST be reproducible for equivalent inputs and
configuration. Pseudonym generation and mapping behavior MUST be deterministic
under documented seeds/rules. The system MUST provide traceable artifacts
(mappings, metadata, logs) sufficient for audit and review.

Rationale: Reliability and compliance require reproducible, inspectable results.

### VII. Robust Error Handling
Engine/model initialization failures, missing resources, unsupported inputs, and
optional-service outages MUST be handled gracefully with actionable user-facing
errors and structured diagnostic logs. Silent failure and unhandled exceptions in
core workflows are prohibited.

Rationale: Anonymization is mission-critical and must degrade predictably.

### VIII. Testability
All engines, engine adapters, and document adapters MUST have automated tests.
Changes to interface contracts, deterministic mapping logic, and failure paths
MUST include unit and integration coverage. Features lacking test strategy and
verification evidence MUST not be merged.

Rationale: Test discipline protects correctness in a sensitive domain.

### IX. Extensibility
The architecture MUST support adding anonymization engines and document adapters
(including PDF, DOCX, XLSX, and future formats) without modifying core
application-layer interfaces. Extensions MUST be introduced via documented plugin
or adapter points.

Rationale: Planned extensibility avoids repeated architectural rewrites.

### X. Minimal Invasive Changes
Existing working anonymization scripts and engine logic MUST be preserved with
minimal invasive modification. Integration code MUST wrap or orchestrate
existing behavior instead of refactoring validated core algorithms.

Rationale: Preserve proven behavior while enabling productization.

## System Boundaries and Non-Goals

- The project MUST focus on integrating and productizing existing anonymization
  capabilities into a standalone desktop application.
- The project is not intended to implement a new NER or anonymization model
  from scratch.
- The project MUST NOT depend on cloud inference services for core workflows.
- The project MUST avoid unnecessary heavy frameworks and architecture
  complexity; any added complexity MUST be justified by clear functional need.

## Development Workflow and Quality Gates

- Each specification and implementation plan MUST include an explicit
  constitution compliance check covering all ten principles.
- Feature plans MUST define incremental milestones with acceptance criteria and
  rollback-safe behavior between milestones.
- Pull requests MUST document impacted layers, interface changes, deterministic
  behavior impact, and error-handling strategy.
- Merge approval MUST require passing automated tests for changed engines,
  adapters, and integration paths.
- Any exception to a principle MUST include a written rationale, scope,
  mitigation, and sunset/remediation plan.

## Governance

This constitution is the highest-priority engineering policy for this repository.
In case of conflict, this document takes precedence over informal practices.

Amendment procedure:
- Propose changes via pull request that includes rationale, impacted principles,
  and template/document updates.
- Obtain approval from project maintainers.
- Include a Sync Impact Report in the amended constitution.

Versioning policy (semantic versioning):
- MAJOR: Backward-incompatible governance changes or removal/redefinition of
  principles.
- MINOR: New principle/section or materially expanded mandatory guidance.
- PATCH: Clarifications, wording improvements, and non-semantic refinements.

Compliance review expectations:
- Plans, specs, tasks, and pull requests MUST explicitly confirm compliance with
  this constitution.
- Reviewers MUST block approval when mandatory clauses are unmet or
  non-compliance is undocumented.
- Periodic governance review MUST occur at major milestones to verify
  continued alignment with local-first anonymization goals.

**Version**: 1.0.0 | **Ratified**: 2026-03-07 | **Last Amended**: 2026-03-07
