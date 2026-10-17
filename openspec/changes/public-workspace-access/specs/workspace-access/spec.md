## ADDED Requirements

### Requirement: Accurate inaccessible workspace state
The UI SHALL distinguish an unavailable session from an empty workspace and SHALL avoid mounting server-backed pages when session establishment is denied.

#### Scenario: Origin denied
- **WHEN** the session endpoint rejects the request origin
- **THEN** the workspace shows an access-unavailable explanation without zero-record or indefinitely loading source states

### Requirement: Authenticated private preview
Temporary website access SHALL require verified credentials over HTTPS before trusted loopback forwarding, while rejecting foreign origins and unsafe requests without same-origin proof.

#### Scenario: Anonymous request
- **WHEN** a client requests a protected website/API without credentials
- **THEN** the gateway denies access before forwarding to the local development service

#### Scenario: Cross-origin mutation
- **WHEN** an authenticated browser submits a mutation from an unrelated origin
- **THEN** the gateway rejects it before rewriting trusted upstream headers or executing the action
