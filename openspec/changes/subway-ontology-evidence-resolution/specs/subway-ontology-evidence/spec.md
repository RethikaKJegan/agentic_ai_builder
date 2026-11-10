## ADDED Requirements

### Requirement: Task-specific evidence recovery
The ontology SHALL describe available alternative evidence routes before declaring a
business task blocked and SHALL distinguish an unavailable parent record from facts
available on its child records.

#### Scenario: Budget availability without reservation history
- **WHEN** a question asks whether a specified amount fits a line item's budget
- **THEN** the retrieved ontology identifies line-item availableAmount and requested
  amounts as sufficient comparison inputs without requiring historical reservations

#### Scenario: Conditional requisition validation
- **WHEN** a question concerns a purchase order without a supplied requisition link
- **THEN** requisition approval evidence is not presented as a global prerequisite

#### Scenario: Approval parent absent
- **WHEN** a stage has no matching approval parent
- **THEN** its own recorded status, dates and actors remain evidence for stage history
  without asserting final approval status or guessing a parent identity

### Requirement: Immutable and isolated evidence supplement
The system SHALL preserve v4 definitions and packages, apply the independently hashed
supplement only to the exact Subway owner/workspace/version/content hash and expose
source citations with the resolution. It SHALL NOT change workflow behavior or grant
new query, write or business-action authority.

#### Scenario: Other client or snapshot
- **WHEN** the ontology belongs to another owner, client, historical version or content
- **THEN** no Subway resolution supplement is attached
