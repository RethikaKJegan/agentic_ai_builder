## ADDED Requirements

### Requirement: Workflow-bound action classification
Business composition SHALL classify a connector's side effects for the standalone
workflow it will generate while retaining normal Registry and runtime approvals.

#### Scenario: Automatic procurement connector used in a business investigation
- **WHEN** a Gmail connector configured for automatic procurement is selected for a standalone draft
- **THEN** planning recognizes its workflow-bound write behavior and requires the existing exact action approval before execution

#### Scenario: Missing resource authority
- **WHEN** an action lacks an authorized destination or schema-valid explicit inputs
- **THEN** planning continues to reject that action
