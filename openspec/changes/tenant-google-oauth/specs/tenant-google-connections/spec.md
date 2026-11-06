## ADDED Requirements

### Requirement: Isolated clients can authorize their own Google accounts
The system SHALL enable Google web authorization using tenant-local encrypted
connection storage and SHALL preserve the initiating tenant and browser binding
through the public callback.

#### Scenario: Google returns without the application login cookie
- **WHEN** a valid state-bound routing cookie and OAuth browser cookie return
- **THEN** the callback reaches only its initiating workspace
- **AND** its account credentials are stored only for that workspace and owner

#### Scenario: Routing evidence is forged or expired
- **WHEN** routing evidence is invalid, expired or does not match callback state
- **THEN** the proxy rejects it without forwarding the provider code

### Requirement: Google workflow tools use owned accounts only
The system SHALL supply existing Google workflow connectors in isolated workspaces
and SHALL require an owned, consented Google connection before a connector can
access Google. Existing operator accounts SHALL remain outside client workspaces.

#### Scenario: An account is selected for a workflow
- **WHEN** a client selects a connected account with the required scopes
- **THEN** planning and execution bind only that owned account
- **AND** an unbound tool or foreign account is rejected without token fallback
