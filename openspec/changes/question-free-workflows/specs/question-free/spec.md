## ADDED Requirements

### Requirement: Automatic generation does not request clarification answers
When question-free mode is enabled, the system SHALL create a scoped workflow from the objective and available context without follow-up questions. Missing recipients, identifiers, definitions, relationships or scheduling details SHALL NOT be invented. If safe executable work cannot be compiled, the system SHALL create a visibly blocked draft with declarative limitations and no external actions.

#### Scenario: Missing route requirement
- **WHEN** interpretation returns missing requirements or unsupported scheduling details
- **THEN** generation returns a saved blocked workflow draft with an empty questions list

#### Scenario: Missing action input
- **WHEN** action planning cannot resolve a required business input
- **THEN** generation returns a blocked draft instead of a business-input form

### Requirement: Blocked drafts cannot be executed or misreported as complete
Blocked question-free drafts SHALL carry unresolved requirements in canonical workflow metadata, and the composition integrity check SHALL prevent their removal. They SHALL fail validation/approval and SHALL NOT activate schedules or submit provider actions. Authorization and malformed input failures SHALL remain errors.

#### Scenario: Forged removal of blockers
- **WHEN** a client removes the unresolved requirements from a blocked composition workflow
- **THEN** composition verification rejects the modified control metadata

### Requirement: Preliminary symptom review uses available bounded evidence
For qualitative investigations, planners SHALL prefer independent authorized text-record reads when text filters or joins are unavailable. They SHALL disclose truncation, distinguish potential causes from a specific diagnosis and recognize overlapping reads of the same source. Exact complete-search or statistical requirements SHALL remain blocked when unsupported.

#### Scenario: No engine identifier or text-search operator
- **WHEN** a user asks for likely causes from available records
- **THEN** planning may produce bounded historical evidence review without an identifier question or invented symptom filter

#### Scenario: Unresolved runtime query
- **WHEN** query execution is blocked on unresolved meaning or unsupported operations
- **THEN** the UI shows an execution limitation without an answer form or claim that the query ran
