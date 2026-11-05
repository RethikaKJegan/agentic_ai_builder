## ADDED Requirements

### Requirement: Scoped immutable action-instance plans
The backend SHALL validate versioned bounded action DAGs against current registered capabilities, scope, schemas and authority and retain distinct instances of repeated capabilities.

#### Scenario: Repeated Gmail action
- **WHEN** two actions use the same mail capability
- **THEN** they retain separate inputs, action IDs, approvals and receipts

### Requirement: Typed verified bindings
Bindings SHALL use discriminated types and bounded declared field paths, require dependency completion, validate types and distinguish generated content from execution authority.

#### Scenario: Spreadsheet URL handoff
- **WHEN** a spreadsheet creation returns a verified ID and URL
- **THEN** generated email content may consume that actual URL and an approved send uses an independently authorized recipient

### Requirement: Existing execution and recovery boundaries
Plans SHALL compile through existing composition, Registry, CrewAI and graph execution and persist checkpoints through existing runtime and case storage.

#### Scenario: Restart after a write
- **WHEN** a completed action is reopened after restart
- **THEN** its receipt is retained and the write is not repeated; uncertain writes require reconciliation

### Requirement: Phase 1 scope
Implementation SHALL exclude adaptive replanning, background scheduling and frontend changes.

#### Scenario: Missing authority
- **WHEN** a required account, destination or approval is absent
- **THEN** execution remains blocked without inventing authority
