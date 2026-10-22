## ADDED Requirements
### Requirement: Detailed usage and limits reference
Governance SHALL present Organization Policies, Usage & Limits, and Oversight & Accountability. Numerical limits SHALL appear in Usage & Limits rather than agent safeguards. Usage & Limits SHALL provide Execution, Delegation and Spending tables with limit, configured value, recorded usage and scope, expandable source/measurement/period explanations and retrieval time.
#### Scenario: Scope separation
- **WHEN** revision-level agent limits and aggregate usage are returned
- **THEN** they appear separately without inferred utilization or period
#### Scenario: Missing values
- **WHEN** usage or limits are not reported
- **THEN** they appear as Not reported while genuinely reported zero remains zero
### Requirement: Read-only preservation
The redesign SHALL use existing monitoring reads, preserve policy pagination and audit inspection, and avoid changes to backend, authorization, configuration, databases or workflow behavior.
#### Scenario: Navigation and inspection
- **WHEN** users navigate reference sections and inspect records
- **THEN** no backend mutations are submitted
