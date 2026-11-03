## ADDED Requirements
### Requirement: Business source lifecycle
Business Ontology SHALL expose profiling and current metadata for both configured owned sources, compare current metadata to its saved source revisions and identify affected module/rule/workflow references without inventing mappings.

#### Scenario: Source schema changes
- **WHEN** a bound database publishes a new metadata revision
- **THEN** the workspace shows field and type changes with qualified module/rule/workflow impacts
- **AND** routine unchanged automatic checks preserve query availability

### Requirement: Bounded record exploration
Business Ontology SHALL allow explicit read-only exploration of configured source datasets, with bounded rows/fields/bytes and current ownership, generation, metadata revision and credentials checked before and after the read.

#### Scenario: Source authority changes during retrieval
- **WHEN** a source is disconnected or its generation/revision changes during a record read
- **THEN** no retrieved records are returned to the caller

### Requirement: Retired legacy workspace
The application SHALL expose a single Business Ontology workspace and SHALL NOT initialize the legacy ontology backend or serve its public routes. Shared source evidence and immutable historical audit records SHALL remain separate from retired business-definition features.

#### Scenario: Legacy workspace requested
- **WHEN** an old ontology public route is requested
- **THEN** no legacy definition, profiling or record mutation is performed
