## ADDED Requirements
### Requirement: Complete coordinator results
The coordinator SHALL use authenticated persisted outputs for completed actions rather than truncated observability snapshots.
#### Scenario: Growing supplier thread
- **WHEN** a supplier reply is beyond the UI trace size bound
- **THEN** the coordinator receives that reply from the full run result without widening public traces
