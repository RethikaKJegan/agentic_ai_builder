## ADDED Requirements
### Requirement: Recorded procurement delegation
Native procurement SHALL use the existing bounded delegation runtime to review source records with registered master and specialist agents. Deterministic BOQ ingestion SHALL use original authorized tool results, not model-generated replacement rows. Existing published action revisions SHALL remain unchanged.

#### Scenario: Starting a new project
- **WHEN** a reviewed published procurement workflow starts
- **THEN** the source run records specialist spawning, delegated tasks, returned results and master synthesis before deterministic BOQ preparation

### Requirement: Configured and executed communication
Agent communication SHALL show the configured source hierarchy before starting and actual source-run communication after starting, using the existing inspector.

#### Scenario: Backend failure
- **WHEN** communication cannot load
- **THEN** the error is visible and no missing-project message conceals it

### Requirement: Correct connection diagnosis
Missing procurement routes on the Builder API SHALL report missing integration, rather than claiming the service is unrelated.

#### Scenario: Unstarted project
- **WHEN** status is refreshed before the project has started
- **THEN** the UI shows the project is ready to start and no false connection error
