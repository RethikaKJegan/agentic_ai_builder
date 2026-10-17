## ADDED Requirements
### Requirement: Owned cloud connections
The system SHALL encrypt saved credentials, restrict access to the authenticated owner/workspace,
and permit only verified TLS connections to supported public Atlas or Supabase endpoints.
#### Scenario: Unauthorized connection access
- **WHEN** another owner requests a saved connection
- **THEN** the system returns not found without exposing configuration or credentials
### Requirement: Durable real metadata discovery
The system SHALL enqueue bounded discovery after connecting and preserve the last successful snapshot on failure.
#### Scenario: Disconnect while profiling
- **WHEN** a connection is disconnected during a job
- **THEN** that job cannot publish metadata or reactivate the connection
### Requirement: Inspectable discovery
The UI SHALL show connection and profiling status separately and actual discovered metadata with stable IDs, revisions and coverage.
#### Scenario: Metadata refresh
- **WHEN** profiling completes after a schema change
- **THEN** the latest snapshot and added/removed/changed dataset or field information are available
