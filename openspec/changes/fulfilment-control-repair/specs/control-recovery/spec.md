## ADDED Requirements
### Requirement: Aligned control shape
The model control transport SHALL enforce existing reason and task bounds and JSON object encoding.
#### Scenario: Exhausted task capacity
- **WHEN** no task slots remain
- **THEN** delegate is absent from the transport choices
### Requirement: Pure extraction recovery
Fulfilment SHALL allow at most one new extraction after a recorded schema failure only when the failed action has no tools or external effects.
#### Scenario: Failed send
- **WHEN** the stopped action contains a notification or write
- **THEN** recovery does not execute or replay it
