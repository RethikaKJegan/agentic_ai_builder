## ADDED Requirements

### Requirement: Durable query clarification
A typed query with unresolved business meaning SHALL pause before source reads, persist the original question, and prevent downstream actions. The existing blocked run state SHALL remain authoritative.

#### Scenario: Ambiguous measure
- **WHEN** the query planner supplies a nonempty clarification
- **THEN** the read task is persisted as needs-input with no query job or result
- **AND** the question remains visible after restart and browser refresh

### Requirement: Explain historical clarification without rewriting history
Owner-scoped presentation SHALL expose saved query clarification text from existing failed runs without changing persisted executions.

#### Scenario: Previously failed read
- **WHEN** a historical read failed with ACTION_INPUT_REQUIRED and contains a typed query clarification
- **THEN** its presentation identifies the missing business definition and preserves the stored run

### Requirement: Preserve external-effect safety
Read-only query clarification SHALL NOT imply external-write uncertainty merely because a later email exists. Actual or uncertain write attempts SHALL retain reconciliation requirements. Unknown legacy write classification SHALL fail closed.

#### Scenario: Read before pending email
- **WHEN** a reviewed read query requests clarification before the email step
- **THEN** the UI offers explicit new-plan preparation rather than external-effect reconciliation

#### Scenario: Earlier write attempt
- **WHEN** an external write has already been attempted
- **THEN** reconciliation remains required and the inline clarification generation action is unavailable

### Requirement: Explicit definition preserves selected account
An owner MAY supply a business definition to generate a new reviewable workflow using existing planning APIs, selected account, resources and scope. No query, approval or provider effect SHALL automatically execute.

#### Scenario: User supplies definition
- **WHEN** the user submits the explicit definition
- **THEN** the original goal plus that definition is planned with the same Google connection
- **AND** the original blocked run remains unchanged
