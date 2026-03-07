# Contract: Canonical Anonymization Result Schema

## Required Fields
- `anonymized_text: string`
- `mapping: MappingArtifact`
- `entities: EntityReplacement[]`
- `engine_id: string`
- `processing_metadata: ProcessingMetadata`

## Optional Fields
- `pseudonym_metadata: object`

## Normalization Rules
- Backend-specific structures must be converted before leaving engine layer.
- Empty entity extraction is represented as an empty list, not null.
- Mapping must contain origin metadata matching `engine_id`.
