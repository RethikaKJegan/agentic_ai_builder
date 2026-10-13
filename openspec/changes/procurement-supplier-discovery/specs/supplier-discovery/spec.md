## ADDED Requirements
### Requirement: Reviewed supplier discovery
The system SHALL discover suppliers through registered search/page tools, retain actual evidence, and require reviewed contact selection before RFQ preparation.
#### Scenario: Unknown contact
- **WHEN** no email is published in the collected evidence
- **THEN** the candidate remains incomplete and cannot be selected for outreach
#### Scenario: Unavailable research provider
- **WHEN** a search or public page fails with a recorded provider availability error
- **THEN** the coordinator SHALL retain the failed run, try the bounded search fallback where applicable, and continue other sections
- **AND** authorization, cancellation and budget failures SHALL still stop the project
### Requirement: Public page boundary
The page reader SHALL restrict requests to bounded public HTTPS pages and reject private addresses and unreviewed redirects.
#### Scenario: Private URL
- **WHEN** a URL resolves to a private or local address
- **THEN** no page request is performed
### Requirement: Unified communication
The communication view SHALL display project-owned exact run revisions and recorded events in one namespaced graph.
#### Scenario: Colliding node names
- **WHEN** related runs contain identical node identifiers
- **THEN** each remains separately identifiable with its original run and trace
