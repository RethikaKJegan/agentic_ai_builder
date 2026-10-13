## ADDED Requirements

### Requirement: Opt in bounded creation
The extension SHALL expose separately approved spreadsheet and tab creation tools only with explicit provisioning enablement and Google edit consent. Inputs SHALL declare project identity, a stable creation key, tabs and bounded literal headers.

#### Scenario: Disabled default
- **WHEN** provisioning is not enabled
- **THEN** original extension connector behavior remains available and new creation tools cannot execute

### Requirement: Preserve existing tables
Adding tabs SHALL reuse matching existing tables and fail on header conflicts without overwriting existing cells. New tabs and headers SHALL be initialized atomically.

#### Scenario: Conflicting tab
- **WHEN** an existing requested tab has different headers
- **THEN** no tab/header mutation is performed

### Requirement: Durable setup identity
Creation SHALL journal intents by workspace, project and creation key, preserve confirmed ownership and refuse blind uncertain-write repeats. Operator reconciliation SHALL verify provider creation markers and the reviewed manifest before marking a result complete.

#### Scenario: Repeat after uncertainty
- **WHEN** an earlier provider creation result is unknown
- **THEN** the same setup remains blocked until verified read-only reconciliation, without a duplicate create

### Requirement: Reviewed write proposals
The procurement helper SHALL define six tracking tables and creation tools SHALL return exact proposed write targets. Proposals SHALL NOT authorize writes until bound to a separately reviewed workflow.

#### Scenario: Created ID used for later rows
- **WHEN** a new resource is returned
- **THEN** subsequent record writes still require exact reviewed metadata.sheet_write_targets
