## ADDED Requirements
### Requirement: Inspect recorded node execution
The editor SHALL expose observations, decision evidence, outputs and chronological events for a node within a selected authorized run.
#### Scenario: Inspect a branch
- **WHEN** the user selects a run and clicks a condition node
- **THEN** the inspector displays recorded expression, evaluated value, selected outcome and successor edges
### Requirement: Preserve evidence boundaries
The system SHALL redact sensitive values, bound snapshots and identify unavailable historical evidence.
#### Scenario: Old run has metadata only
- **WHEN** a selected event lacks observation or output snapshots
- **THEN** the inspector explains that the evidence was not captured without generating an explanation
