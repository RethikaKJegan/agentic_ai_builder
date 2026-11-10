## ADDED Requirements

### Requirement: Canonical typed-query handoff
Automatic workflow planning SHALL normalize the known data.plan_query response envelope to its query child when binding whole output to tool.workflow_data_query query and both declared child schemas agree exactly. Other producer identities, binding kinds, source paths and targets SHALL NOT be reinterpreted.

#### Scenario: Planner repeats a whole-response binding
- **WHEN** automatic planning binds the entire data.plan_query response to the query tool query input
- **THEN** the binding selects the declared query child before validation
- **AND** account scope, dependency, typed query validation and exact-payload approvals remain enforced

### Requirement: Actionable mismatch diagnostics
Rejected incompatible bindings SHALL expose action, source path, target path and declared schemas to bounded planner correction without supplying runtime values.

#### Scenario: Unsupported mismatch
- **WHEN** another binding has incompatible declared types
- **THEN** validation rejects it with structured diagnostics and does not coerce its value
