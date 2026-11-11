## ADDED Requirements

### Requirement: Query model projections respect dataset ownership
For bounded catalogues with no authorized joins, the model response schema SHALL
couple each permitted base dataset to its own projected field identifiers. It SHALL
retain supported clarification and aggregate queries. Existing source validation
SHALL remain authoritative. Relationship or oversized catalogues SHALL retain the
existing unconstrained response schema and validation rather than losing capability.

#### Scenario: Foreign projected field
- **WHEN** a query selects a base dataset and a projected field from a different dataset
- **THEN** the constrained model response schema rejects that combination

### Requirement: Correction feedback names the failed validation rule
Generated-query validation feedback SHALL identify the trusted validator rule,
without source rows or rejected model prose. Retry and authority limits SHALL remain.

#### Scenario: Invalid query after model output
- **WHEN** the trusted typed query validator rejects generated output
- **THEN** the bounded correction hint states that specific validation rule

### Requirement: Rejected query validation is diagnosable
The runtime SHALL record bounded trusted query validation feedback for each rejected
planning output, including the final failed attempt. It SHALL NOT log rejected model
prose or source rows in that diagnostic. Execution ownership checks SHALL remain.

#### Scenario: Both model attempts fail
- **WHEN** two model outputs violate typed query validation
- **THEN** two rejection events identify the validation rules and no source query runs
