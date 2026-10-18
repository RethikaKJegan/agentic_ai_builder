## ADDED Requirements
### Requirement: Complete source inspection from detailed graph
The detailed graph SHALL let users inspect every source mapping of an entity
through bounded pages and navigate relationship field pairs using qualified source
labels without granting edit or execution permissions.

#### Scenario: Entity has more than one page of source mappings
- **WHEN** a user opens an entity with more than 100 mappings
- **THEN** the view displays the visible and total counts and permits loading all remaining mappings

#### Scenario: Inspect a relationship linking field
- **WHEN** a user selects either field of a displayed relationship
- **THEN** the existing field details open for that exact source-qualified field

#### Scenario: Read-only or historical inspection
- **WHEN** the user has read permission only or the graph is historical
- **THEN** source navigation remains available and review mutations remain disabled
