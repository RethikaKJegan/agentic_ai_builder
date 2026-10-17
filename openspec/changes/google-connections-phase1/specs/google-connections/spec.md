## ADDED Requirements
### Requirement: Owned Google connections
The system SHALL manage durable Google connections scoped to the authenticated workspace and subject, with encrypted credentials and safe public responses.
#### Scenario: Authorize an account
- **WHEN** a user completes a valid browser-bound, unexpired, single-use OAuth transaction
- **THEN** the backend validates Google identity and persists actual granted scopes
- **AND** no credentials are returned to the browser
### Requirement: Lifecycle and isolation
The system SHALL support verification, incremental authorization, reconnect and local disconnect without modifying existing workflow credential bindings.
#### Scenario: Revoked or disconnected connection
- **WHEN** Google rejects a refresh grant or the connection is locally disconnected
- **THEN** the system prevents credential use and reports an accurate connection state
