## ADDED Requirements

### Requirement: Native procurement workflow setup
The existing MESH planner SHALL produce a reviewed procurement plan using supplied spreadsheet links and discovered headers. Unknown project terms SHALL remain explicit and editable before execution.

#### Scenario: Generate and publish
- **WHEN** an authorized operator supplies a procurement objective with requirements and vendor links
- **THEN** the existing editor shows source mappings and project context for review and publication

### Requirement: Approved RFQ submission
The integrated coordinator SHALL use canonical runtime actions and a dedicated human gate for every external mutation. RFQs SHALL become OPEN only after confirmed Gmail message/thread identifiers.

#### Scenario: Rejected or uncertain send
- **WHEN** an RFQ send is rejected or its result is unknown
- **THEN** the project stops without automatically replaying the email

### Requirement: Parent workflow authority
Procurement actions SHALL remain bound to the exact active parent workflow revision.

#### Scenario: Disabled parent
- **WHEN** the parent is disabled or replaced
- **THEN** further provider mutations are prevented, including pending child actions
