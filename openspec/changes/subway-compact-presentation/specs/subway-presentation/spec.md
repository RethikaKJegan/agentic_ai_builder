## ADDED Requirements

### Requirement: Compact Subway demonstration presentation
The application SHALL use the concise “Demo data” indicator in newly generated Subway demonstration reports and downstream communication content, and SHALL retain canonical source provenance in audit records. Existing stored runs and exact approved external payloads SHALL remain unchanged. Presentation changes SHALL apply only to Subway content.

#### Scenario: New demonstration report feeds external content
- **WHEN** a Subway demonstration report contains the legacy verbose label
- **THEN** the report SHALL normalize it to “Demo data” before payload approval
- **AND** monetary values, currency groups and citations SHALL remain unchanged

#### Scenario: An existing report is inspected
- **WHEN** a Subway user opens a report, workflow detail panel or trace
- **THEN** its display copy SHALL show the concise label
- **AND** its stored audit and immutable source definitions SHALL remain unchanged

### Requirement: Authorized revision-zero knowledge loading
The Knowledge Map SHALL accept a registered ontology revision of zero and load the workflow's exact authorized demonstration ontology pin. An unrelated workspace overview failure SHALL NOT prevent a valid pinned snapshot from loading. Existing other-tenant fallback behavior SHALL be preserved.

#### Scenario: Subway workflow completes using revision-zero demo ontology
- **WHEN** the authorized snapshot endpoint returns the saved demo ontology
- **THEN** the Knowledge Map SHALL render its concepts and verified usage
- **AND** SHALL NOT silently substitute another ontology for an unavailable demonstration pin
