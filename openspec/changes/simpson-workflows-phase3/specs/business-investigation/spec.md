## ADDED Requirements
### Requirement: Grounded graph planning
The backend SHALL produce version-pinned investigation DAGs using only registered capabilities and saved Phase 2 concepts, mappings and dependencies.
#### Scenario: Inspection and warranty request
- **WHEN** the user requests comparison and warranty readiness for a complaint
- **THEN** the graph includes linked evidence retrieval, independent readiness work, comparison and report composition without unrelated replacement actions
### Requirement: Deterministic validation and control
The backend SHALL reject cycles, unreachable nodes, invalid input bindings and incomplete branch coverage, and evaluate conditions with true, false and unknown outcomes.
#### Scenario: Published report
- **WHEN** a report is published without activity-completion evidence
- **THEN** the workflow preserves the missing activity evidence
### Requirement: Durable authorized execution
The backend SHALL persist node intentions/results, lease execution, run independent tasks concurrently, preserve completed checkpoints and recheck authorization/version/source bindings on execution and resumption.
#### Scenario: Interrupted node
- **WHEN** execution is resumed after lease expiry
- **THEN** completed nodes are preserved and eligible incomplete work uses stable execution identifiers and bounded retry budgets
### Requirement: Bounded CrewAI evidence analysis
CrewAI SHALL receive bounded source-qualified evidence, use no arbitrary tools/code, and return validated interpretations that cannot grant permissions or manufacture confirmed business conclusions.
#### Scenario: Unsupported agent claim
- **WHEN** an agent asserts approval or confirmed identity
- **THEN** the assertion is rejected or marked unsupported and cannot change backend decisions
### Requirement: Terminal operations and evidence
Planning, validation, execution, input, resume, cancel and inspection SHALL be available from the backend and terminal with persisted audit and explicit gaps.
#### Scenario: Missing complaint identifier
- **WHEN** the objective lacks an identifier
- **THEN** the run waits for typed input and supplied assertions remain distinct from company evidence
