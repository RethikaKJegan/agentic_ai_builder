## ADDED Requirements
### Requirement: Exact bounded federation
The service SHALL execute supported reviewed aggregate plans through a PostgreSQL fact fragment and bounded dimension fragments with complete join validation, exact partial states and final global ordering.

#### Scenario: Large facts and weighted averages
- **WHEN** a supported fact source exceeds the application row limit and dimensions and intermediate states fit their budgets
- **THEN** execution aggregates complete facts in PostgreSQL, validates complete cross-source relationships and returns the same weighted aggregates as complete scalar execution

#### Scenario: Invalid keys hidden by filters
- **WHEN** any required complete join domain has null, duplicate target or unmatched source keys
- **THEN** execution rejects the query without returning partial totals even if filters would exclude those rows

### Requirement: Auditable fragment evidence
The service SHALL expose bounded execution strategy, fragment read windows, checked source counts and intermediate transfer measurements without exposing executable programs or credentials.

#### Scenario: Independent snapshots
- **WHEN** a query combines sources from different databases
- **THEN** the result discloses independent snapshots and each fragment read window
