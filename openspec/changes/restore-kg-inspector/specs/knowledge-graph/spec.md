## ADDED Requirements
### Requirement: Read-only desktop inspector
The KG canvas SHALL expose a desktop Inspect sidebar for selected entities and
relationships using existing metadata and provenance. It SHALL NOT restore record
exploration, business edits, technical permission edits or extra generation modes.
#### Scenario: Inspect a relationship
- **WHEN** an edge is selected by mouse or keyboard
- **THEN** Inspect shows its meaning, status, rationale, field links and evidence/provenance trace
#### Scenario: Scope changes
- **WHEN** a selected item is excluded by the current connection or graph filter
- **THEN** its old details are not displayed
#### Scenario: Inspect an entity
- **WHEN** a node is selected
- **THEN** Inspect shows only source mappings permitted by the current connection display filter
