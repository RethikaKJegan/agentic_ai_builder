## ADDED Requirements

### Requirement: Approved creation with bounded report content
The system SHALL register a separate new-spreadsheet report capability requiring an immediate approval gate, bounded scalar report rows, stable creation identity and verified provider receipt. It SHALL preserve existing-document write ceilings and SHALL NOT accept an existing spreadsheet destination.

#### Scenario: Create a report once
- **WHEN** an approved report action supplies valid tabs, headers and rows
- **THEN** the connector creates a new spreadsheet containing that exact report in one creation request and verifies the stored contents
- **AND** a repeat with the same creation identity reuses the verified receipt without another creation

#### Scenario: Unknown or changed report outcome
- **WHEN** verification fails or an existing creation identity is reused with different content
- **THEN** the connector refuses automatic recreation and requires reconciliation of the original approved intent

#### Scenario: Plan a database report
- **WHEN** a user requests findings in a new spreadsheet
- **THEN** the planner receives the registered create-report schema and can produce a gated report action without inventing an existing destination
