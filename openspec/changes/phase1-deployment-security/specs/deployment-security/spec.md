## ADDED Requirements

### Requirement: Production identity and origin enforcement
The system SHALL refuse production startup until the deferred Google Workspace authentication is implemented and SHALL reject unauthorized origins in the current local/test deployment.

#### Scenario: Production startup without trusted authentication
- **WHEN** production startup is requested before Google Workspace authentication is implemented
- **THEN** startup fails closed without issuing a development session

#### Scenario: Anonymous mutation
- **WHEN** an anonymous caller attempts a workflow mutation
- **THEN** the backend returns 401 without performing the mutation

#### Scenario: Unauthorized origin
- **WHEN** a request supplies an origin outside the configured exact allowlist
- **THEN** the backend returns 403

### Requirement: Reliable private API transport
The system SHALL use a server-configured private upstream and SHALL preserve authenticated statuses, safe errors and streaming bodies.

#### Scenario: Unavailable backend
- **WHEN** connection to the configured backend fails
- **THEN** the proxy returns a canonical unavailable error without replaying mutations

### Requirement: Durable planning
The system SHALL persist scoped planning job state and SHALL expose cancellation and result retrieval.

#### Scenario: Browser disconnect
- **WHEN** a browser disconnects after submitting a planning job
- **THEN** an authorized caller can retrieve the job status and result
