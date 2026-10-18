## ADDED Requirements
### Requirement: Trusted physical execution
The system SHALL choose database pushdown only for supported validated operations and SHALL explain bounded fallback for other plans.

#### Scenario: Large aggregate
- **WHEN** a supported aggregate reads more than 5,000 source rows within database budgets
- **THEN** the database computes its complete result and only bounded results are transferred

### Requirement: Complete validation and evidence
The system SHALL reject invalid joins, unsupported runtime values and exceeded budgets without partial totals and SHALL report execution strategy and transfer evidence.

#### Scenario: Unmatched key outside the filter
- **WHEN** any source join key is unmatched even outside the requested filter
- **THEN** execution fails before returning results

#### Scenario: PostgreSQL snapshot
- **WHEN** a PostgreSQL plan runs
- **THEN** its validation and result reads share a read-only repeatable-read snapshot
