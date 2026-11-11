## ADDED Requirements

### Requirement: Authorized reusable knowledge map
The frontend SHALL use existing scoped APIs to display the active workspace's
ontology, with reusable rendering independent of customer names. It SHALL reset
state on scope/workflow/run changes and ignore stale asynchronous results.

#### Scenario: Scope changes during fetch
- **WHEN** a user changes authorized workspace while ontology is loading
- **THEN** previous knowledge disappears immediately and late responses cannot populate the new view

### Requirement: Exact provenance and historical qualification
Planned and executed concepts SHALL be associated through exact recorded IDs.
Successful steps or similar labels SHALL NOT establish concept usage. Missing
history, unresolved mappings and current-ontology fallback SHALL be labelled.

#### Scenario: Query without concept mapping
- **WHEN** a query has field references but no recorded concept association
- **THEN** source references remain visible and concept usage is unavailable

### Requirement: Unified workflow interface
The existing workflow SHALL provide Workflow, Steps, Reports, Knowledge Map and
Background views, with one Details entry and Validate/Run controls. All existing
authorization, scheduling and exact-payload approvals SHALL remain enforced.

#### Scenario: Run requires workflow approval
- **WHEN** a validated workflow is started by an authorized approver
- **THEN** the UI presents explicit review before calling existing approval and execution APIs
