## ADDED Requirements
### Requirement: Essential Knowledge graph controls
The Knowledge graph tab SHALL expose regeneration, automatic metadata refresh,
connection selection, search and semantic status filtering, with a readable graph.
It SHALL NOT expose actual-record exploration or business/technical editing panels.
#### Scenario: Combined and single-connection views
- **WHEN** the user selects all connections
- **THEN** the graph includes available entities and cross-connection relationships
- **WHEN** the user selects one connection
- **THEN** only that connection's source mappings and relationships entirely within that connection appear
#### Scenario: Existing planner knowledge remains available
- **WHEN** workflow creation retrieves KG context
- **THEN** the same backend semantic metadata and source-selection guards remain in use regardless of the display filter
