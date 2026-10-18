## ADDED Requirements

### Requirement: Operator-controlled cumulative usage budgets
The live launcher SHALL default to enforcing cumulative token and cost budgets.
An explicit server environment setting SHALL allow the operator to disable those
two cumulative caps without changing reviewed workflow revisions. The runtime
SHALL continue recording reservations and confirmed usage, including actual cost
above a disabled cost cap. Finite per-request token capacity, model/tool call
limits, retries, deadlines, authorization and action approvals SHALL remain active.

#### Scenario: Research returns after substantial coordinator usage
- **WHEN** cumulative usage budgets are disabled and the coordinator has consumed its old token allowance across prior turns
- **THEN** another permitted turn receives its finite per-request capacity and its confirmed usage is recorded

#### Scenario: Calls remain bounded
- **WHEN** the model-call ceiling is exhausted with cumulative usage budgets disabled
- **THEN** the runtime denies the next invocation before calling the provider

#### Scenario: Default policy
- **WHEN** no usage-budget override is configured
- **THEN** existing cumulative budget enforcement remains unchanged
