## ADDED Requirements

### Requirement: Preserve acceptance intent
Release remediation SHALL retain scenario coverage and assert actual persisted behavior through the supported interface. Unavailable external checks SHALL remain explicitly blocked.

#### Scenario: Current interface replaces legacy controls
- **WHEN** an acceptance test references retired navigation or lifecycle controls
- **THEN** the test uses the current supported interface
- **AND** retains its original persistence, permission and safety assertions

### Requirement: Isolated reproducible qualification
Verification SHALL use explicit disposable stores before imports and SHALL NOT modify shared data or perform real external actions.

#### Scenario: Bootstrap incident investigation
- **WHEN** independent logs or backups are inspected
- **THEN** the investigation remains read-only
- **AND** unprovable equivalence is reported honestly

### Requirement: Drain retains live ownership
A supervisor SHALL start lease windows after acquiring the transaction lock,
renew only live ownership, and renew throughout parallel and singleton shutdown.

#### Scenario: Parallel consumer drains beyond the initial lease
- **WHEN** a supervised parallel consumer is finishing accepted work
- **THEN** the live singleton group claim is renewed until the drain finishes
- **AND** an expired or replaced owner cannot revive its claim

### Requirement: Factory imports have no store side effects
Importing API factories SHALL NOT initialize a default database. Explicit ASGI app
lookup SHALL retain its supported application construction behavior.

#### Scenario: Configure an isolated application
- **WHEN** a launcher imports the application factories before selecting its store
- **THEN** no SQLite connection is opened by the import

### Requirement: Inspect pending commands safely
A pending adaptive mutation SHALL NOT prevent a scoped read-only refresh. Refresh
SHALL NOT submit a second mutation or authorize an uncertain action replay.

#### Scenario: Refresh during a pending drive command
- **WHEN** an operator refreshes adaptive state while a command is in flight
- **THEN** only the scoped state read is repeated
- **AND** command execution remains disabled until its outcome is handled
