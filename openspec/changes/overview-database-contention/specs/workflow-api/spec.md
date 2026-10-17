## ADDED Requirements
### Requirement: Nonblocking overview reads
Overview polling SHALL use read-only database transactions and retain correct workspace-scoped latest run, active run and pending approval counts.
#### Scenario: Writer active during polling
- **WHEN** another connection has a write transaction
- **THEN** the WAL overview read completes without acquiring a competing write lock
### Requirement: Retryable storage contention
Database busy or locked errors SHALL return a safe retryable availability response rather than claiming invalid workflow data.
#### Scenario: Concurrent save contention
- **WHEN** a workflow save cannot obtain a database lock within its bounded wait
- **THEN** the API reports API_DATABASE_BUSY without leaking SQL or data
