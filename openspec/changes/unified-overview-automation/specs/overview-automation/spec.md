## ADDED Requirements

### Requirement: Backend-owned Overview routing
The system SHALL use bounded structured AI interpretation of authorized tenant context when enabled and SHALL preserve legacy dispatch when disabled.

#### Scenario: Read-only and unsupported requests
- **WHEN** a request selects a read-only path or lacks supported sources
- **THEN** external-write capabilities are excluded or a precise limitation is returned without execution

### Requirement: Reviewed recurring semantic query
The system SHALL reuse the existing scheduler and consent checks and SHALL vary only reviewed date bounds using the logical occurrence time and timezone.

#### Scenario: Delayed recurring occurrence
- **WHEN** an occurrence runs late or is retried
- **THEN** its date interval derives from its persisted scheduled due time and all other query semantics and destinations remain pinned

### Requirement: Existing Overview review
The system SHALL present workflow and recurrence review in the existing Overview without requiring cron input.

#### Scenario: Unapproved proposal
- **WHEN** a user submits a recurring request
- **THEN** no schedule or provider write occurs until workflow and recurring authorization succeed

### Requirement: Durable preparation through the existing queue
The system SHALL reuse existing planning jobs for asynchronous Overview generation and SHALL preserve cancellation and scoped retry identity.

#### Scenario: Cancellation after an inert stage commits
- **WHEN** generation is cancelled while preparation is running
- **THEN** its queue result is discarded and schedule activation is denied without deleting history or executing external actions
