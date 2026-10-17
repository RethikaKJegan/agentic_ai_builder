## ADDED Requirements

### Requirement: Correct transaction intent
The system SHALL perform read-only API queries without acquiring the SQLite writer reservation and SHALL bound lock waits.

#### Scenario: Concurrent API reads
- **WHEN** a writer transaction is open and a read-only API query runs
- **THEN** the query succeeds from a consistent read snapshot without acquiring a writer lock

### Requirement: Durable activation preparation
The system SHALL prepare external triggers outside database transactions and atomically revalidate release and revision identity before activation.

#### Scenario: Concurrent activation
- **WHEN** two operations prepare against the same expected release
- **THEN** only one conflicting release can become active and the other operation records failure and cleanup

### Requirement: Verified database portability
The system SHALL preserve identities, order, revisions, approvals and idempotency through versioned SQLite/PostgreSQL persistence and migration.

#### Scenario: Migration validation
- **WHEN** a migration is prepared
- **THEN** row contents and sequence state are validated before persistence cutover

### Requirement: Coordinated workers
The system SHALL coordinate worker claims, expose health and backlog, and avoid replaying uncertain external writes after restart.

#### Scenario: Worker crash during external effect
- **WHEN** a worker disappears after persisting an invocation intent
- **THEN** recovery does not automatically repeat the external effect
