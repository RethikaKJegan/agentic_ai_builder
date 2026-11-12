## ADDED Requirements

### Requirement: Consistent authorized metadata selection
Intent transport SHALL constrain identifier choices to advertised metadata. Before
workflow approval, metadata selection SHALL include the exact owned dataset of
every selected canonical field and endpoints of every selected supported
relationship, within existing selection limits. It SHALL not create a relationship
or grant execution permission from source names, similarities or model prose.

#### Scenario: Model omits a selected field's owning dataset
- **WHEN** a field identifier is known in current authorized metadata but its source was omitted
- **THEN** the metadata view includes that exact source within the existing dataset limit
- **AND** the resulting selection passes unchanged strict catalogue validation before planning

#### Scenario: Unknown identity or oversized source set
- **WHEN** any selected identity is unknown/foreign or the derived source set exceeds the existing bound
- **THEN** selection is rejected and no workflow or query authority is granted
