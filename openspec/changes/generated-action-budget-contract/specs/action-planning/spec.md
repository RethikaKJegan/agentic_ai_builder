## ADDED Requirements
### Requirement: Generated action budgets follow registered operation kinds
The server SHALL normalize newly generated draft call allowances against registered capabilities before validation and approval, without changing saved or explicitly submitted plans or relaxing aggregate, retry, schema or agent limits.
#### Scenario: Model step allocated a tool call
- **WHEN** a generated model action has zero model calls and one tool call
- **THEN** its reviewable draft reserves at least one model call and zero tool calls
#### Scenario: Write step allocated zero tool calls
- **WHEN** a generated write action has zero tool calls
- **THEN** its draft reserves exactly one tool dispatch and still requires exact-payload approval
#### Scenario: Explicit invalid plan
- **WHEN** an explicitly submitted plan has an incompatible budget
- **THEN** validation rejects it with exact action and required allowance feedback
#### Scenario: Aggregate ceiling
- **WHEN** a normalized generated proposal exceeds its approved planning constraints
- **THEN** validation rejects it without increasing the ceiling or dropping requested actions
