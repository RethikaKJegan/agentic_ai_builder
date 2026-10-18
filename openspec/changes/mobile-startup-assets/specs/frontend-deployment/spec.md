## ADDED Requirements
### Requirement: Previously loaded pages retain their static dependencies
Frontend deployments SHALL preserve available static assets from the preceding build without replacing a different file at an existing path.

#### Scenario: A browser reloads a previously rendered workspace page
- **WHEN** its HTML references a static chunk from a retained build
- **THEN** the asset endpoint returns the original bytes and the workspace can hydrate

#### Scenario: Retained asset paths conflict
- **WHEN** a source asset has different bytes from another file at the same relative path
- **THEN** retention fails before copying any files
