## ADDED Requirements
### Requirement: Grounded read-only question planning
The system SHALL generate strict structured plans from owned current metadata and SHALL require an explicit execution request for a saved expiring plan.
#### Scenario: Ambiguous question
- **WHEN** the planner cannot resolve a metric or source
- **THEN** it returns a clarification and performs no source reads
### Requirement: Bounded trustworthy execution
The system SHALL compile only allowed reads and SHALL validate join keys on completely retrieved bounded datasets before returning calculated results.
#### Scenario: Unsafe or incomplete join
- **WHEN** target keys duplicate, source keys are null/unmatched, a limit is exceeded or metadata changes
- **THEN** execution fails with no partial answer
### Requirement: Evidence and isolation
The system SHALL enforce owner/workspace permissions and return source timestamps, row counts, join checks, metric definitions and result limits without exposing credentials.
#### Scenario: Foreign plan
- **WHEN** another owner requests execution of a saved plan
- **THEN** the plan is not found and no cloud read occurs
