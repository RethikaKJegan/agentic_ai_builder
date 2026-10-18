## ADDED Requirements
### Requirement: Explicitly authorized registered database operations
The system SHALL allow CRUD only for owned targets and fields permitted by trusted
policy, actual database authority and exact registered tool grants.

#### Scenario: Read authority alone
- **WHEN** a caller lacks write approval or a dataset/operation/field grant
- **THEN** no write is prepared or executed

### Requirement: Reviewed immutable bounded writes
The system SHALL prepare exact-key operations without writes and require explicit
execution of the owned, unexpired, unchanged server-owned intent.

#### Scenario: Conflicting record
- **WHEN** the record no longer matches its preview
- **THEN** the transaction rolls back and reports conflict without overwriting newer values

#### Scenario: Duplicate execution or uncertain acknowledgement
- **WHEN** execution is repeated or the outcome cannot be established
- **THEN** the durable claim prevents replay and uncertainty remains explicit

### Requirement: Honest cross-source recovery
The system SHALL record independently committed steps and permit reviewed inverse
operations only against unchanged known after-images under current grants.

#### Scenario: A later database fails
- **WHEN** an earlier step committed and a later step definitely failed
- **THEN** the operation reports partial completion and eligible compensation can be reviewed

#### Scenario: Unknown or changed effect
- **WHEN** a step is uncertain or its after-image changed
- **THEN** automatic compensation is rejected and no unconditional Undo is promised
