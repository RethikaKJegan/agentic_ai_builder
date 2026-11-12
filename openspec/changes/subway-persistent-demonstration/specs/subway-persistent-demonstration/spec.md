## ADDED Requirements

### Requirement: Persistent isolated demonstration data
The system SHALL persist versioned modeled Subway records and policies separately from historical sources, scoped to the authenticated Subway workspace and owner.

#### Scenario: Explicit demonstration selection
- **WHEN** a Subway prompt starts with `Use Subway demonstration dataset v1.`
- **THEN** existing planning and tools use only the pinned demonstration datasets and label every result as modeled

### Requirement: Shared execution architecture
The system SHALL execute demonstration queries, investigations and scheduled occurrences through the existing Overview, query engine, Registry, CrewAI, GraphRunner and scheduler.

#### Scenario: Genuine application acceptance
- **WHEN** a selected demonstration investigation is submitted through Overview with configured provider transports
- **THEN** persisted modeled records, deterministic rules and verified evidence produce a report without requiring caller-provided internal query IDs or mocked model decisions

### Requirement: Provenance and source preservation
The system SHALL reject mixed historical/demo identities, preserve source/version hashes in receipts and never describe modeled policies or transactions as verified company operations.

#### Scenario: Historical request
- **WHEN** a request has no explicit demonstration context
- **THEN** demonstration records are unavailable to historical query tools
