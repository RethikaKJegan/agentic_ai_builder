## ADDED Requirements
### Requirement: Connected existing canvas
The existing Semantic Intelligence canvas SHALL resolve identifier-only concepts only from unambiguous primary/foreign key evidence and SHALL retain other concepts via truthful dataset ownership links. It SHALL connect business components through source connection/workspace membership, visually distinguishing these links from business meaning.
#### Scenario: Field reference
- **WHEN** a field-only concept resolves unambiguously to a declared referenced dataset entity
- **THEN** its source mapping appears under that existing entity without modifying saved server mappings
#### Scenario: Unrelated dataset
- **WHEN** a dataset has no business relationship
- **THEN** its actual source membership connects it to the same canvas without a fabricated business relationship
### Requirement: Preserve execution and review authority
Rendering SHALL leave backend graph payloads, workflow source bindings, execution joins and approval state unchanged, and relationship reviews SHALL continue to use original server relationship IDs/directions.
#### Scenario: Inspect membership
- **WHEN** a user inspects a source-membership edge
- **THEN** the canvas shows metadata evidence and offers no business-relationship approval control
