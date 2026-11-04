## ADDED Requirements
### Requirement: Actionable investigation failures and details
The system SHALL preserve typed failure diagnostics, permit only validated bounded
model correction or eligible explicit recovery, and expose editable request and
connection context in Workflow details without altering an approved composition.

#### Scenario: Retryable infrastructure failure
- **WHEN** storage contention prevents a step
- **THEN** it is distinguished from missing business evidence and model output errors
- **AND** no external action is silently replayed

#### Scenario: Review workflow details
- **WHEN** a user opens Workflow details
- **THEN** the question and connection settings are available there
- **AND** changed settings generate a new immutable plan requiring normal approval

#### Scenario: New run after failure
- **WHEN** a new run follows a failed run of the same owned approved revision
- **THEN** only relevant sanitized diagnostic hints may inform model correction
- **AND** failed results never become source evidence or execution permission
