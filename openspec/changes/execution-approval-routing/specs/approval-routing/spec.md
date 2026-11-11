## ADDED Requirements

### Requirement: Execution approval is not a missing business input
In question-free mode a supported route SHALL proceed to normal action planning
when its missing_requirements contains only unambiguous execution-approval notices.
The planner SHALL NOT treat future workflow review or per-action approval as missing
source, recipient, resource, business meaning or schedule information.

#### Scenario: Compose analysis and approved tools
- **WHEN** email, Sheets, Calendar, web search or their combination requires review
- **THEN** a complete request produces a normal draft with applicable existing gates

### Requirement: Actual gaps and execution authority remain guarded
Normalization SHALL NOT remove unresolved inputs, missing scopes, denied access,
ambiguous consent requests or mixed approval/input statements. It SHALL NOT execute
a tool, activate a schedule or grant approval. Existing stored requests SHALL retain
their idempotent result.

#### Scenario: Unknown recipient or missing access
- **WHEN** a requirement includes an unknown destination or unavailable permission
- **THEN** the requirement remains unresolved and no external action executes
