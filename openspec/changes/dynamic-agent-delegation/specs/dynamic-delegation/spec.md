## ADDED Requirements

### Requirement: Runtime-selected specialist tasks
The runtime SHALL allow a configured master to choose registered child agents and task inputs at execution time and consume their results before its next decision.

#### Scenario: Different requests choose different specialists
- **WHEN** two requests lead the master to choose different child agents
- **THEN** only the chosen task instances execute in each run and each instance has a distinct UUID

### Requirement: Persisted bounded delegation
The runtime SHALL enforce reviewed agent membership, input/output schemas, approvals, cumulative budgets, task/round limits and immutable revision checks for every turn and child call.

#### Scenario: Invalid batch is denied before child execution
- **WHEN** a master requests an undeclared specialist or exceeds its task limit
- **THEN** no child from that batch executes and the failure is recorded

### Requirement: Actual communication evidence
The UI SHALL show spawned agents and task/result handoffs from the exact selected run with observations, concise decision explanations and outputs.

#### Scenario: Child finishes
- **WHEN** a specialist returns a validated result
- **THEN** a recorded return handoff links the child invocation to its master and appears in the run diagram

#### Scenario: Multiple task instances return to the same master
- **WHEN** two instances of one specialist and a further specialist return results
- **THEN** the diagram displays all task UUIDs and clickable task/result connections without a layout crash
- **AND** placement uses forward relationships while the displayed connections retain actual return directions
