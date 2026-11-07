## ADDED Requirements

### Requirement: Case reads require a ready source anchor
Connected plans SHALL request missing case identifiers before compilation and
SHALL NOT dispatch an unanchored case evidence read.

#### Scenario: List request selects a case-only reader
- **WHEN** selected case reads have no exact complaint or engine identifier
- **THEN** planning requests explicit input using existing clarification metadata
- **AND** no executable composition is persisted

#### Scenario: Explicit identifier resolves clarification
- **WHEN** an authorized user supplies a typed complaint identifier
- **THEN** planning creates a fresh pinned preparation for that identifier
- **AND** preserves the prior preparation and current source authority
