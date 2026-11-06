## ADDED Requirements

### Requirement: Authenticated Simpsons identity
The website SHALL verify separate Simpsons credentials and issue a signed,
expiring account-bearing session. The backend SHALL require independently signed
short-lived client authority on every client request, including session bootstrap.

#### Scenario: Forged authority
- **WHEN** a caller supplies an expired assertion, forged account or development cookie
- **THEN** the Simpsons backend denies the request without loading company resources.

### Requirement: Complete client execution boundary
The Simpsons deployment SHALL pin one workspace and subject across existing chat,
planning, retrieval, ontology, Registry, runtime and background workers. It SHALL use
a separate provisioned application store and explicitly allowlisted company sources.

#### Scenario: Complete workflow
- **WHEN** an authenticated Simpsons user plans and executes a supported workflow
- **THEN** context, saved versions, queries, jobs and run records remain within Simpsons.

#### Scenario: Foreign references
- **WHEN** the user requests a foreign source or supplies a different workspace identity
- **THEN** access is rejected at the backend or source-ownership boundary.

### Requirement: Fail closed routing and provisioning
The website SHALL never fall back from Simpsons to the shared backend. Provisioning
SHALL copy only explicitly selected company definitions, context and source bindings,
re-encrypt credentials and exclude shared queues and histories.

#### Scenario: Wrong backend or mixed store
- **WHEN** configuration selects the shared upstream or a store contains another company
- **THEN** configuration or startup fails and no shared data is returned.
