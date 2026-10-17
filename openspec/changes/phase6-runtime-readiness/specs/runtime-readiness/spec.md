## ADDED Requirements

### Requirement: Recoverable bounded runtime history
The system SHALL provide workspace-scoped, filtered, paginated run and event reads using durable order and SHALL serialize refreshes, preserve confirmed data after interruption and stop frequent terminal-run polling.

#### Scenario: Interrupted event updates
- **WHEN** an event request fails and reconnects
- **THEN** events resume after the last confirmed sequence without duplicates or invented completion

### Requirement: Exact approval and trigger readiness
The system SHALL enforce the exact revision gate authority and display trigger preparation, release state, safe configuration and poll health without exposing credentials.

#### Scenario: Wrong approval role
- **WHEN** a subject lacks the gate role or approval permission
- **THEN** the server rejects the decision and the UI offers no authorized decision action

### Requirement: Explicit governance scope
The system SHALL distinguish browser-only drafts from read-only backend enforced revision rules and SHALL NOT grant server authority using local role flags.

#### Scenario: Browser policy changes
- **WHEN** a local policy draft is changed
- **THEN** it is labeled browser-only and no production policy mutation is implied
