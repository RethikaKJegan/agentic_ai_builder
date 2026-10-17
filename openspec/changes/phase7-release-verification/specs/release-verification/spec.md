## ADDED Requirements

### Requirement: Reproducible complete verification
The project SHALL provide a default browser verification command covering the current UI and SHALL run clean-install frontend checks and backend regression checks with actual required runtime dependencies.

#### Scenario: Current lifecycle controls
- **WHEN** the default browser suite runs
- **THEN** it uses Save draft and separate validation, approval, publication and activation controls
- **AND** no removed control or automatic approval is assumed

### Requirement: Isolated complete journey and negative cases
The release checks SHALL exercise real canonical APIs with isolated data, exact revision persistence, current grants, runtime events and safe failure recovery, and SHALL preserve origin, permission, idempotency, concurrency and worker recovery boundaries.

#### Scenario: Controlled failure
- **WHEN** a test run fails at a known node
- **THEN** the failed node and safe reason are visible and retries do not duplicate external effects

### Requirement: Evidence-based release decision
Release evidence SHALL distinguish passing, failing, unavailable and deferred checks and SHALL NOT claim production readiness before actual production identity and the complete required lifecycle are verified.

#### Scenario: Deferred public identity
- **WHEN** Google Workspace login is deferred
- **THEN** public protected access remains denied and authenticated public lifecycle verification is explicitly unexecuted
