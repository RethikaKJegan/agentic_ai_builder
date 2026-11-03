## ADDED Requirements
### Requirement: Business prompt workflow generation
The existing builder SHALL generate supported read-only investigation graphs from business prompts while preserving general automation generation.
#### Scenario: Supported complaint investigation
- **WHEN** the user submits a supported complaint comparison/readiness prompt
- **THEN** the UI shows the saved validated backend graph with branches and parallel tasks
### Requirement: Durable asynchronous UI execution
Generation and execution SHALL use owner-scoped durable jobs and display actual saved backend states after refresh.
#### Scenario: Browser reload during execution
- **WHEN** a user reloads while a run is executing
- **THEN** the UI resumes polling that run without creating a duplicate paid invocation
### Requirement: Inspectable evidence and results
The UI SHALL show node results, source-backed reports and missing input, with ontology details behind an optional evidence action.
#### Scenario: Incomplete evidence
- **WHEN** an investigation completes with missing facts
- **THEN** the report explains gaps without presenting warranty approval or physical identity as established
### Requirement: Preserving deployment
The authorized website rollout SHALL preserve authentication, source connections, workflow data and immutable ontology history.
#### Scenario: Knowledge activation
- **WHEN** the tested knowledge package is activated
- **THEN** it creates an explicit new saved version and retains earlier versions
