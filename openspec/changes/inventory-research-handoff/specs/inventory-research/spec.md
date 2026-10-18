## ADDED Requirements

### Requirement: Pass through the verified research result
An inventory compiler v1 workflow with exactly one research child sharing the
coordinator output schema SHALL wait for its sole delegated result and validate
it before returning it to the graph, without another coordinator model call.
This behavior SHALL require the expected external-risk output and research-only
capabilities. Other workflows SHALL retain normal model synthesis. Specialist
failure or invalid output SHALL stop execution before Google approvals or writes.

#### Scenario: Helper finishes after delegation
- **WHEN** the compiled inventory coordinator delegates its sole research task
- **THEN** it waits and forwards the validated helper result without another model decision

#### Scenario: General workflow
- **WHEN** the workflow lacks the inventory compiler marker or has different output schemas
- **THEN** its normal coordinator synthesis remains active

#### Scenario: Invalid helper result
- **WHEN** a helper returns an invalid result or fails
- **THEN** the coordinator fails before any report is created
