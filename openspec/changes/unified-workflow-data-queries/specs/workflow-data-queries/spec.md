## ADDED Requirements

### Requirement: Account-scoped workflow queries
The system SHALL expose current authorized data-query metadata and typed query
planning/execution to connected workflows without requiring case identifiers for
population queries.

#### Scenario: Population request without case ID
- **WHEN** a supported request filters or aggregates multiple records
- **THEN** a metered model action prepares a typed query and the backend validates it against the current account catalogue
- **AND** case-reader selection errors receive at most one planning correction

### Requirement: Durable query results
The system SHALL submit existing durable query jobs and resume dependencies only
after obtaining a validated result, with explicit coverage and provenance.

#### Scenario: Worker interruption during query
- **WHEN** a worker stops after a read-only durable query submission
- **THEN** the resumed workflow reattaches to the same job identity without another model call or tool-budget charge

#### Scenario: Pagination or sample
- **WHEN** query results exceed the display limit
- **THEN** statistics remain calculated over the complete matching population
- **AND** sampled evidence is rejected as population input

### Requirement: Recurring query authorization
The system SHALL require exact reviewed query meaning in recurring consent and
revalidate the current account metadata before each occurrence.

#### Scenario: Changed meaning or metadata
- **WHEN** recurring query content differs from consent or current metadata differs from the workflow pin
- **THEN** execution stops before querying data or sending downstream outputs
