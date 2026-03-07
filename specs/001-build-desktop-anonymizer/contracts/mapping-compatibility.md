# Contract: Mapping Compatibility and Deanonymization

## Export Policy
- MVP exports canonical mapping artifacts only.

## Required Metadata
- `schema_version`
- `origin.engine_id`
- `origin.generated_at`

## Validation Workflow
1. Validate schema version support.
2. Validate required metadata exists.
3. Validate origin engine wrapper is available.
4. Route deanonymization through origin engine wrapper.

## Failure Behavior
- If any validation fails, operation must stop with actionable error.
- System must not produce partial or guessed deanonymized output.
