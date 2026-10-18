## ADDED Requirements
### Requirement: Source-scoped workflow database tools
The builder SHALL derive database scope from current owned metadata and SHALL
execute database actions only through exact Registry assignments and trusted adapters.
#### Scenario: A workflow references a different dataset
- **WHEN** a database tool requests a dataset outside its published scope
- **THEN** execution is denied before source I/O
### Requirement: Concrete reviewed database writes
Database writes SHALL reference an immutable prepared operation linked to the same
run and SHALL require a current exact runtime human approval before commit.
#### Scenario: A prepared operation changes before execution
- **WHEN** source state or authority differs from the reviewed operation
- **THEN** execution is refused and no automatic retry overwrites newer data
### Requirement: Planned and actual database evidence
Configuration SHALL show selected source scope and planned tools, and Execution
SHALL show actual source/result references with separately loaded permitted previews.
#### Scenario: A database workflow is inspected
- **WHEN** the user opens Configuration or Execution
- **THEN** planned metadata is distinguishable from actual recorded invocation results
