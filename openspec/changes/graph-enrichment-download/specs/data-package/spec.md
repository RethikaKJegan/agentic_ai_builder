## ADDED Requirements
### Requirement: Non-operational enrichment package
The package SHALL create synthetic relational tables only in a new dedicated schema, with no stock, incoming purchase order or pricing inputs and no foreign keys to original tables.
#### Scenario: Import data
- **WHEN** the supplied package is loaded into an isolated test database
- **THEN** all CSV rows and declared relationships validate and pre-existing source rows remain unchanged
### Requirement: Honest workflow isolation
The operator guide SHALL state that newly discovered tables may affect source selection and describe separate workspace isolation and same-workspace verification.
#### Scenario: Preserve the workflow prompt
- **WHEN** an operator follows the guide
- **THEN** the original prompt is retained verbatim and separate Sheet, email and meeting approvals remain required
