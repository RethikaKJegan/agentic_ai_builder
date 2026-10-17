## ADDED Requirements

### Requirement: Exact persisted baseline and separate working draft
The UI SHALL retain a separate immutable server baseline, track all supported working changes and preserve them across delayed reads, server refreshes and browser-tab notifications.

#### Scenario: Delegated agent edit during loading
- **WHEN** a delegated template is edited while a workflow fetch is pending
- **THEN** the edit remains dirty and recoverable after the response arrives
- **AND** the server version advances only after a confirmed save or an explicit resolution choice

### Requirement: Explicit safe conflict resolution
The editor SHALL detect divergent server revisions and offer explicit comparison, export, confirmed discard/reload and non-overlapping three-way rebase without automatically saving or changing an active release.

#### Scenario: Two editors save different fields
- **WHEN** another editor saves a newer revision
- **THEN** current local edits are retained and the changed server revision is identified
- **AND** rebase applies only non-overlapping edits to the latest baseline and still requires Save and fresh authorization

### Requirement: Accurate safe API feedback
The UI SHALL display safe structured codes, request/field references, recovery actions and uncertain outcomes, and SHALL NOT display raw exceptions or automatically replay uncertain mutations.

#### Scenario: Save response is lost
- **WHEN** a mutation has an unconfirmed transport result
- **THEN** the UI retains the working draft and retry identity and explains the unknown outcome
- **AND** a read-only reload/check may confirm state without submitting the effect again
