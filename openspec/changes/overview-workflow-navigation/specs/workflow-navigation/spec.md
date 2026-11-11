## ADDED Requirements

### Requirement: Successful generation opens workflow details
The UI SHALL navigate each newly prepared Overview composition to its specific Workflows detail page, including one-time and recurring work. The full graph and action/schedule approval controls SHALL be displayed there, not embedded in Overview. Navigation SHALL NOT approve or execute work.

#### Scenario: New composed workflow
- **WHEN** generation produces a prepared composition
- **THEN** the UI opens that composition under Workflows with its durable request reference

#### Scenario: Pending generation resumes
- **WHEN** a pending request restored on Overview finishes
- **THEN** the UI opens the resulting workflow without submitting another request

#### Scenario: Clarification or failure
- **WHEN** generation needs clarification or fails
- **THEN** the prompt and specific feedback remain visible on Overview

### Requirement: Workflow review survives navigation and refresh
The UI SHALL restore the owner-scoped Overview request on the workflow page and verify its composition matches the URL. Schedule and execution controls SHALL retain existing review requirements. Returning to Overview SHALL NOT automatically reopen a previously completed request.

#### Scenario: Schedule detail reload
- **WHEN** the generated workflow page is refreshed
- **THEN** its saved schedule proposal or activation state is loaded without creating or activating work

#### Scenario: Wrong owner or composition
- **WHEN** the saved request belongs to another owner or differs from the URL composition
- **THEN** its review and action controls are not rendered
