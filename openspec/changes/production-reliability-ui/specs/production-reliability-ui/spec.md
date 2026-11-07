## ADDED Requirements

### Requirement: Trusted shared capacity
Server configuration SHALL bound shared provider windows and reserve configured
runtime slots for accounts. Model and request content SHALL NOT increase limits.

#### Scenario: Another account uses a shared credential
- **WHEN** the configured shared provider window is exhausted
- **THEN** another account using that credential is deferred without invocation

### Requirement: Current evidence synchronization
Bounded authorized polling SHALL create new immutable graph revisions or mark
unavailable projections stale. Existing workflow pins SHALL remain unchanged.

#### Scenario: Source content changes
- **WHEN** a supported source poll observes changed records
- **THEN** a new current revision is saved and the prior revision remains historical

### Requirement: Evidence backed operational UI
The existing investigation workspace SHALL display bounded backend graph and
recovery evidence. Administrative alerts SHALL require monitoring authority.
All consequential actions SHALL continue through existing authorization.

#### Scenario: Unknown external effect
- **WHEN** an invocation outcome is uncertain
- **THEN** the UI displays reconciliation requirements without a blind replay action

### Requirement: Controlled reliability qualification
Tests SHALL distinguish isolated process/database/restore evidence from
multi-host, live-provider and production deployment qualification.

#### Scenario: Restoration drill
- **WHEN** isolated durable stores are backed up and restored
- **THEN** original checkpoints, waits, receipts, events and graph versions remain available
