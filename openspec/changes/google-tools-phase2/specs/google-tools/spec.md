## ADDED Requirements
### Requirement: Explicit revision connection
The runtime SHALL use a selected owned Google connection for supported Google actions and SHALL fail closed on missing ownership, scope or connection state.
#### Scenario: Selected account is disconnected
- **WHEN** a selected account is disconnected
- **THEN** subsequent tool operations fail without falling back to legacy credentials
### Requirement: Background binding
Procurement child workflows and polling SHALL preserve their owning immutable revision's selected connection.
#### Scenario: A later revision changes the selected account
- **WHEN** a later revision selects another account
- **THEN** existing runs retain the connection of their original revision
### Requirement: Existing account management compatibility
Phase 2 SHALL preserve Phase 1 account-management behavior and existing unselected workflow bindings.
#### Scenario: A legacy workflow runs
- **WHEN** a workflow has no selected Google connection
- **THEN** its existing connector path is retained
