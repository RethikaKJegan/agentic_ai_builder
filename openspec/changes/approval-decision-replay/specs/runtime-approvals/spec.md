## ADDED Requirements
### Requirement: Approval decision replay is idempotent
The runtime SHALL return the current run state when an authorized approver submits the same decision for an already decided gate, irrespective of transport retry key. Replay SHALL preserve the original decision identity, audit events, execution state and action receipts. Conflicting decisions SHALL remain rejected and all existing workspace, revision and gate authorization checks SHALL precede replay.
#### Scenario: Stale approval after execution
- **WHEN** an authorized browser repeats approval after the gate has been approved and the workflow has finished
- **THEN** current completed state is returned without new audit events or action execution
#### Scenario: Conflicting or unauthorized replay
- **WHEN** a request reverses an existing decision or lacks gate authority
- **THEN** the request is rejected and stored history remains unchanged
