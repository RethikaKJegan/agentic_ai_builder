## ADDED Requirements

### Requirement: Shared website routing
The configured public website SHALL reach the existing workspace backend without Google login or an added password challenge.

#### Scenario: Website session
- **WHEN** a visitor opens the configured HTTPS website
- **THEN** the API session and authorized workspace collections load through the same-origin proxy without an origin error

### Requirement: Original origin validation
The HTTPS gateway SHALL validate the original browser origin and unsafe-request origin proof before translating the API request to the trusted loopback origin.

#### Scenario: Foreign origin
- **WHEN** a request presents an unrelated Origin or cross-site fetch context
- **THEN** the gateway rejects it before forwarding it to the application

### Requirement: Precise temporary access cleanup
The system SHALL remove the rejected password credentials and unfinished access UI while preserving existing workflows, data, tool connections and prior corrections.

#### Scenario: Existing data
- **WHEN** temporary access changes are removed
- **THEN** saved workflows and configured integrations remain available

### Requirement: Bounded workflow discovery
Workflow collections and overview snapshots SHALL return at most fifty workflow revisions per page, preserve the true workspace total and expose a stable keyset cursor. The UI SHALL expose first/next navigation and SHALL not replace a newly selected page with a stale background response.

#### Scenario: Large workspace
- **WHEN** the workspace contains more than fifty workflows
- **THEN** the initial page and its matching overview load without scanning every workflow document and subsequent pages remain reachable without deleting records
