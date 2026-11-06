## ADDED Requirements

### Requirement: Local archive onboarding preserves provenance
The system SHALL analyze the supplied local MongoDB archives, preserve original
archives and record hashes, collection counts, sampled schema evidence, restore
exclusions and derived-copy repairs before exposing Subway sources.

#### Scenario: Archives are restored for Subway
- **WHEN** the administrator prepares the supplied central and finance dumps
- **THEN** only selected business collections are restored into separate Subway databases
- **AND** original archives remain unchanged and restore evidence is retained

### Requirement: Subway source access remains tenant bound
The system SHALL pin restored source endpoints and use a collection-scoped reader
without write privileges, while enforcing authenticated workspace and owner checks
through application retrieval and workflow execution.

#### Scenario: Another tenant or endpoint is requested
- **WHEN** a read substitutes another owner, database, connection or endpoint
- **THEN** access is denied before retrieving source records

### Requirement: Subway business knowledge uses the existing workflow
The system SHALL expose an evidence-backed Subway ontology and immutable bounded
read package through existing metadata, planning, Registry and runtime interfaces.
Definitions SHALL distinguish source observations from verified policies and joins.

#### Scenario: Subway plans a bounded evidence read
- **WHEN** an authenticated Subway user requests store evidence through normal planning
- **THEN** the server supplies the pinned Subway knowledge package
- **AND** the existing workflow runtime reads only current authorized Subway bindings

### Requirement: Existing Simpsons access is preserved
The system SHALL retain Simpsons credentials, source bindings, saved ontology and
workflow authority when Subway onboarding is deployed.

#### Scenario: Both clients sign in after onboarding
- **WHEN** Simpsons and Subway users log in separately
- **THEN** each resolves to its own workspace and ontology
- **AND** cross-client source access is denied
