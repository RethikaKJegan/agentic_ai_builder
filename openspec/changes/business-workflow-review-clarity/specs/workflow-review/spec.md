## ADDED Requirements
### Requirement: Separate execution limitations from missing setup
Read-only investigation coverage caveats SHALL remain visible without blocking setup; actual required inputs, identities, access or write setup SHALL remain unresolved until supplied.

#### Scenario: Supported bounded investigation
- **WHEN** a read-only draft with no required inputs explicitly limits matching to returned identifiers and discloses sampled coverage
- **THEN** those notes are preserved as report limitations rather than activation setup requirements

#### Scenario: Required input or write
- **WHEN** a draft requires a case identifier or write capability
- **THEN** its unresolved setup is not removed by caveat classification

### Requirement: Understandable business contribution
The workflow evidence view SHALL show human-readable business terms, definitions and affected workflow steps before optional source quotations and technical hashes.

#### Scenario: Client reviews ontology usage
- **WHEN** the client opens the contribution panel
- **THEN** business knowledge and workflow effect are visible without opening technical evidence, and original source evidence remains available on demand
