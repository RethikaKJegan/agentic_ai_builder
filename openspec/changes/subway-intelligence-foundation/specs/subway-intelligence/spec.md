## ADDED Requirements

### Requirement: Tenant-scoped natural-language query planning
Subway Overview requests SHALL use source-backed semantic metadata selection and
the registered reviewed full-data query executor, preserving generic capabilities
for other tenants and immutable historical workflows.

#### Scenario: Unknown business terminology
- **WHEN** the request uses a synonym absent from dataset names
- **THEN** the existing intent model selects relevant authorized concept/field IDs
- **AND** unsupported spending measures or store/site equivalence require clarification

### Requirement: Verified execution provenance
Completed Subway reads SHALL retain exact query/source/field/join/version evidence
through the existing runtime and Knowledge Map, without granting access or
equating observed execution with approved business policy.

#### Scenario: Normal Overview execution
- **WHEN** an authorized supported Subway question is submitted
- **THEN** its typed query binds automatically and executes via Registry/CrewAI/GraphRunner
- **AND** persisted results and map usage match the selected tenant/version

### Requirement: Safe failure and compatibility
Failures SHALL retain sanitized request/correlation diagnostics and actionable
typed API errors. Existing Simpsons, generic queries, UI design and source data
SHALL remain compatible.

#### Scenario: Uncertain or unauthorized query
- **WHEN** a relationship is unsupported, authority is stale or storage is busy
- **THEN** execution fails with the appropriate typed limitation/error and no fabricated result
