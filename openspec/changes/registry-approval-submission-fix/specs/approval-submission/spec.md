## ADDED Requirements

### Requirement: Pending Registry approvals can enter workflow review
A validated exact workflow revision SHALL be eligible for approval submission when its Registry assignments are authorized or pending approval and every referenced tool is covered. Submission SHALL NOT issue tool approval evidence or approve, publish, activate or execute a workflow. Denied assignments, missing assignments and unresolved setup SHALL remain blockers.

#### Scenario: Tool grants await human approval
- **WHEN** all referenced tools have authorized or pending-approval assignments and no other blockers exist
- **THEN** submission records a review request while preserving the validated state and pending grants

#### Scenario: Report destination remains unresolved
- **WHEN** a validated revision contains an unresolved report destination
- **THEN** submission returns the bounded setup requirement and Registry reason codes through the existing error details rendered by the UI

#### Scenario: A tool is denied or uncovered
- **WHEN** an assignment is denied or a referenced tool lacks an eligible assignment
- **THEN** submission is rejected without recording a review request
