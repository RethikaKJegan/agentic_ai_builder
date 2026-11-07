## ADDED Requirements

### Requirement: Generated completion actions have consistent execution flags
The planner SHALL normalize a generated action marked optional with an explicit null condition to required before validation. It SHALL NOT remove a real condition, alter explicit proposals or bypass missing inputs and approvals.

#### Scenario: Unconditional requested email
- **WHEN** a generated email action has optional true and when null
- **THEN** its optional flag is normalized to false and the complete plan is validated before review

#### Scenario: Genuine conditional completion
- **WHEN** a conditionally skipped action is named as required completion
- **THEN** validation rejects it and bounded planner feedback identifies the conflict without executing it
