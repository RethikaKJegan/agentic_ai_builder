## ADDED Requirements

### Requirement: Integrated release evidence
The platform SHALL be assessed using current source and explicit test environments.
Unavailable checks SHALL NOT be counted as passing; repeated executions SHALL NOT
be summed as distinct cases. External effects and production changes SHALL require
separate explicit authorization.

#### Scenario: Missing representative staging environment
- **WHEN** multi-host or live-provider acceptance cannot execute with available authority
- **THEN** the release report records a blocker and limits its readiness decision

### Requirement: Preserve the supported data-question entry point
The existing Data Intelligence interface SHALL expose the existing Questions
component and retain its current backend permission and review controls.

#### Scenario: Navigate to questions without starting work
- **WHEN** a reader opens Questions
- **THEN** the question interface is available without planning/executing a query
- **AND** management permission remains required to create a query plan

### Requirement: Isolate eager test imports
Automated verification SHALL configure private bootstrap stores before importing
application modules that eagerly initialize a default application.

#### Scenario: Collect tests or start browser fixtures
- **WHEN** a verification process imports the API module
- **THEN** eager initialization uses a private disposable store
- **AND** a shared/default application store is not selected by omission
