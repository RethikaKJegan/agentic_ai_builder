## ADDED Requirements

### Requirement: Active Subway definitions follow supplied datasets
New Subway planning SHALL use only restored collection concepts, modelling parents,
supported relationships and applicable source-cited rules. Unconnected application
models SHALL NOT enter active package or planner context.

#### Scenario: An archive application has no corresponding dataset
- **WHEN** new Subway planning retrieves ontology evidence
- **THEN** its unconnected model classes and unrelated rules are absent
- **AND** immutable historical versions remain accessible

### Requirement: Correspondence and relationship checks are traceable
Each restored collection SHALL have a matching model and identified service evidence
or an explicit recorded absence. Relationship checks SHALL record exact paths and
bounded native-ID matches without claiming global referential integrity.

#### Scenario: A relationship has sampled matching identifiers
- **WHEN** its evidence is retrieved
- **THEN** sample bounds and unresolved matches remain recorded
- **AND** no automatic join authority is inferred
