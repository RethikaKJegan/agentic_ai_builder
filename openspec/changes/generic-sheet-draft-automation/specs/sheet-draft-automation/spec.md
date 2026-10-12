## ADDED Requirements

### Requirement: Prompt-generated domain workflows
The live planner SHALL expose authorized record-writing capabilities without hardcoded business roles, identifiers or findings.

#### Scenario: Different business prompts
- **WHEN** restaurant and manufacturing workflows are generated and published
- **THEN** each uses its configured records and agent definitions through the same runtime
- **AND** fresh rows trigger checked findings and stored drafts without email submission

### Requirement: Restricted identity-based writes
Record writes SHALL require exact Registry authorization and approved server targets and resolve current rows by identity.

#### Scenario: Sorted or duplicate rows
- **WHEN** records have been sorted
- **THEN** the current identity row is updated
- **AND** duplicate identities or invalid headers fail before writing

#### Scenario: Concurrent creation and literal values
- **WHEN** cooperating application workers save different identities in the same table
- **THEN** writes are serialized with bounded lock acquisition
- **AND** formula-looking text is stored literally

### Requirement: Published execution controls
Automatic writes SHALL require explicit server opt-in and workflow write policy, while default execution retains action approval and runtime limits.

#### Scenario: Forbidden resource or column
- **WHEN** a workflow requests an unapproved table or column
- **THEN** no external write occurs

#### Scenario: Duplicate dispatch and uncertain effects
- **WHEN** a completed review identity is seen again after restart
- **THEN** existing lifecycle deduplication prevents duplicate dispatch
- **AND** uncertain external writes block without automatic replay
