## ADDED Requirements

### Requirement: Correct pure content within existing limits
Source/link validation SHALL run inside the existing bounded model correction
boundary and SHALL still reject unprovided URLs or citations after correction.

#### Scenario: Email content after a confirmed spreadsheet
- **WHEN** generated content invents an unprovided URL
- **THEN** one pure-model correction is allowed within existing ownership/budgets
- **AND** the completed spreadsheet is not recreated

### Requirement: Public research is explicitly configured and privacy bounded
Tenant public research SHALL reuse existing authorized bounded tools only when
server-enabled and SHALL reject known case identifiers and email addresses in queries.

#### Scenario: Complaint identifier in a public query
- **WHEN** a workflow attempts to send its bound complaint ID to search
- **THEN** dispatch rejects the query before contacting a public provider
