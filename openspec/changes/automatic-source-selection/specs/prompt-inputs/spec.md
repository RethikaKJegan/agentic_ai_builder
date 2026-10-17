## ADDED Requirements

### Requirement: Prompt-only source inference
The system SHALL accept one requirement prompt without requiring an input-source mode selection and SHALL provide the planner with authorized workspace source context.

#### Scenario: Connected and additional sources
- **WHEN** a user requests a workflow with existing workspace knowledge or published sources and optionally includes an additional supported source link
- **THEN** the planner receives bounded workspace-scoped source context and the supported source is discoverable without a dropdown

### Requirement: Fresh authorized knowledge
Accepted agents with data-read permission SHALL receive current workspace knowledge as untrusted task data, separately from validated inputs and registered instructions.

#### Scenario: Knowledge changes after planning
- **WHEN** saved knowledge changes before an agent invocation
- **THEN** that invocation receives the current permitted knowledge and no other workspace content

### Requirement: Missing source honesty
The system SHALL preserve unresolved setup requirements for inaccessible, ambiguous or unsupported sources without inventing provider data or granting access.

#### Scenario: A source has no ingested content
- **WHEN** a knowledge source contains only an unsupported URL
- **THEN** the planner is told content is unavailable and no fetched-content claim is made
