## ADDED Requirements
### Requirement: Registered capability composition
The backend SHALL compose only registered executable capabilities into bounded acyclic task plans and Registry-validated temporary agents.
#### Scenario: Different business outcomes
- **WHEN** history, comparison or warranty is requested
- **THEN** only necessary tasks, specialists and compatible tools are configured
### Requirement: Controlled delegation
The existing runtime SHALL enforce prepared task dependencies, scoped context, approved tool operations and verified outputs.
#### Scenario: Premature synthesis
- **WHEN** the master attempts to finish before required tasks return
- **THEN** the workflow rejects the unsupported completion
### Requirement: External effect control
Tool existence SHALL NOT establish missing recipients, calendars, resources or business authority.
#### Scenario: Missing calendar identifier
- **WHEN** an event operation lacks its required resource
- **THEN** preparation requests input and performs no external effect
