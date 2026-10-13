## ADDED Requirements

### Requirement: Durable scoped transactions
The extension SHALL persist domain records and immutable revisions in separate SQLite state, with scoped references, optimistic concurrency and durable transaction idempotency.

#### Scenario: Restart and retry
- **WHEN** the same transaction is retried after reopening the store
- **THEN** its committed result is returned without another revision or synchronization intent

### Requirement: Guard procurement state
The repository SHALL reject illegal lifecycle transitions, incompatible quotations and order closure without explicit authorized buyer evidence and complete accepted quantities.

#### Scenario: Premature closure
- **WHEN** delivery is reported without buyer confirmation
- **THEN** the order cannot close and the transaction has no partial changes

### Requirement: Preserve integration boundaries
Provider resource links and synchronization intents SHALL be persisted without invoking providers or granting connector approval. Original application state SHALL remain unchanged.

#### Scenario: Pending synchronization
- **WHEN** a case revision includes a Sheet projection intent
- **THEN** the revision and pending intent commit together and no external write executes
