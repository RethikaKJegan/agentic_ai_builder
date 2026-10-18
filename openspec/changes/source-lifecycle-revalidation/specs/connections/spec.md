## ADDED Requirements
### Requirement: Stable reconnection identity
Adding the same endpoint and principal SHALL reuse one disconnected connection belonging to the same workspace and owner, after successful verification. Deletion SHALL remove that identity. Credentials SHALL remain encrypted and identity fingerprints SHALL exclude passwords.

#### Scenario: Reconnect the same database
- **WHEN** one disconnected connection has the same endpoint identity
- **THEN** its connection ID is reused and profiling is queued
- **AND** unchanged dataset IDs and matching relationship evidence retain their reviews

#### Scenario: Delete and replace
- **WHEN** a connection is deleted and added again
- **THEN** it receives a new identity and old relationship reviews do not authorize it

### Requirement: Source lifecycle preflight
Planning and relationship execution SHALL exclude unavailable or unverified metadata. Workflow source validation SHALL explain missing, disconnected or profiling connections before checking pinned semantic evidence. Existing execution scopes SHALL remain subject to metadata and credential revision checks.

#### Scenario: Source unavailable
- **WHEN** a workflow references a deleted, disconnected or profiling source
- **THEN** validation returns actionable repair guidance without executing a database operation
