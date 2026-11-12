## ADDED Requirements

### Requirement: Clean actual delivery content
Subway demonstration workflows SHALL prepare reports and email, Calendar and spreadsheet payload content without demonstration prefixes or repeated provenance disclaimers. Financial values, currency grouping, citations, missing evidence and coverage facts SHALL remain accurate. Canonical source/audit provenance SHALL remain unchanged.

#### Scenario: Prepared content flows to an external connector
- **WHEN** a Subway workflow resolves email, Calendar or spreadsheet content
- **THEN** the resolved payload SHALL contain the cleaned report text before exact approval
- **AND** recipients, resource IDs, dates, record keys and approval checks SHALL remain unchanged

#### Scenario: Legacy prepared output is bound to a future delivery
- **WHEN** stored content still includes obsolete presentation prefixes
- **THEN** new delivery input resolution SHALL clean only supported content fields
- **AND** an old approval SHALL NOT authorize a changed payload

#### Scenario: Other tenants or genuine historical sources execute
- **WHEN** the workflow lacks the trusted Subway demonstration source context
- **THEN** its content SHALL remain unchanged
