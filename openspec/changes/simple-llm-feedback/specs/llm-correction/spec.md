## ADDED Requirements

### Requirement: Bounded validation feedback
The planner SHALL supply actionable validation feedback and a secret-checked prior
draft on its existing correction attempt. Runtime model boundaries SHALL allow at
most one correction for invalid JSON or output schema. Correction SHALL preserve
the original inputs and include only safe rule metadata.

#### Scenario: Invalid control output
- **WHEN** a model emits an invalid control object and a correction call is allowed
- **THEN** it receives validation feedback and its corrected output is validated again

#### Scenario: Invalid correction
- **WHEN** the correction is also invalid
- **THEN** the run stops without further correction attempts or tool execution

### Requirement: Preserve execution boundaries during correction
Every correction SHALL reserve a fresh call, recheck authorization/deadlines and
record feedback in the run trace. Tool execution, approval failures, budget
failures, provider failures and unknown external effects SHALL never be replayed
by this loop.

#### Scenario: Budget or external effect failure
- **WHEN** a budget, authorization or external-effect failure occurs
- **THEN** no correction retry is attempted
