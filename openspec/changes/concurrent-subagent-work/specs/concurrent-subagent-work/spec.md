## ADDED Requirements

### Requirement: Master continuation during delegated work
The runtime SHALL allow a master to attach continuation data to a delegated batch and make another decision while child tasks execute.

#### Scenario: Independent master work overlaps a child task
- **WHEN** a master delegates a task with continuation data
- **THEN** its next decision receives continuation and pending task identities while the child can still be running
- **AND** task conditions remain determined by the agent rather than domain-specific runtime rules

### Requirement: Final synthesis includes completed children
The runtime SHALL join all pending required children before accepting a final master output.

#### Scenario: A master attempts to finish with a pending child
- **WHEN** a finish decision arrives while a child result remains uncollected
- **THEN** the runtime joins that child and requests another master decision with its validated result
- **AND** the earlier incomplete output is not published

### Requirement: Bounded concurrent execution and stable handoffs
The runtime SHALL retain existing authorization, schema, task, round, budget and cancellation checks and associate every child handoff with its spawning master invocation.

#### Scenario: Child returns after a later master turn
- **WHEN** the master has continued working before the child returns
- **THEN** both child handoffs still reference the original spawning master invocation
