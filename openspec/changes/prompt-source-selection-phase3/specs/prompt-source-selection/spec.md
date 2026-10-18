## ADDED Requirements
### Requirement: Reviewed business context for source selection
The planner SHALL receive only confirmed current business mappings attached to
supported catalog nodes without receiving source rows or new grants.

#### Scenario: Mapping is not confirmed
- **WHEN** a mapping is suggested, rejected or requires renewed review
- **THEN** it is excluded from confirmed context and cannot authorize a join

### Requirement: Reviewable validated source subset
The Questions UI SHALL show server-derived datasets, required fields, field
purposes and eligible linking pairs before executing a read plan.

#### Scenario: Only one database is required
- **WHEN** a validated plan requires one dataset
- **THEN** only that dataset is selected and unrelated datasets receive no business queries

#### Scenario: A cross-source plan is valid
- **WHEN** datasets connect through eligible supported relationships
- **THEN** qualified linking fields and review states appear in the selected graph

#### Scenario: Clarification or stale context
- **WHEN** a request requires clarification or its saved context changes
- **THEN** clarification exposes no selected read plan and stale execution remains rejected
