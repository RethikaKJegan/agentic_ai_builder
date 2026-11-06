## ADDED Requirements

### Requirement: Independent Subway authentication
The website SHALL authenticate Subway credentials into a signed Subway account
and route requests exclusively to the Subway backend with its own assertion key.

#### Scenario: Password substitution
- **WHEN** a Subway password is supplied for the Simpsons email or vice versa
- **THEN** login is rejected without issuing a session.

### Requirement: Empty isolated onboarding stage
Subway SHALL use its own marked application store with no source connections,
company data or ontology definitions. Planning, runtime and mutations SHALL remain
disabled during this authentication-only stage.

#### Scenario: Foreign resource access
- **WHEN** Subway requests a Simpsons resource or supplies a Simpsons assertion
- **THEN** the resource request or authentication is denied.

### Requirement: Preserve Simpsons access
Existing Simpsons credentials, sessions, data bindings and execution behavior SHALL
remain valid when Subway is registered.

#### Scenario: Independent login verification
- **WHEN** both client accounts sign in after deployment
- **THEN** each receives its own workspace and only its existing resources.
