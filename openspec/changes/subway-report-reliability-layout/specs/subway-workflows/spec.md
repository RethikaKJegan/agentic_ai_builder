## ADDED Requirements
### Requirement: Report evidence transport preserves all facts
Subway report preparation SHALL eliminate duplicate provenance through reversible references while retaining original durable evidence and all rule outcomes.
#### Scenario: Large reconciliation report
- **WHEN** a report consumes repeated deterministic assessment provenance
- **THEN** its model transport contains every original fact through a shared reference dictionary and the original receipt remains unchanged
### Requirement: Provider errors remain diagnosable
Model transport failures SHALL retain safe typed failure details without storing private exception messages or retrying external effects.
#### Scenario: Provider timeout
- **WHEN** a model transport times out
- **THEN** the run records a model timeout and service-specific recovery guidance rather than an evidence authorization failure
### Requirement: Subway workflow cards fit their layout
Subway workflow cards SHALL use bounded dimensions matching graph layout, preserve action identities and expose full instructions in existing details.
#### Scenario: Long parallel tasks
- **WHEN** long instructions and parallel dependencies appear
- **THEN** cards do not overlap and labels remain bounded with readable initial zoom
