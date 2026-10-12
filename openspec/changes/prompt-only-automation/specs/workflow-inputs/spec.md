## ADDED Requirements

### Requirement: Prompt-only automatic proposals
The system SHALL save known configuration from the initial prompt and obtain changing data from configured triggers or authorized reads.

#### Scenario: Manual start
- **WHEN** an automatic workflow has no event trigger
- **THEN** it declares no run inputs and runs with an empty input object

#### Scenario: Event start
- **WHEN** an automatic workflow declares event inputs
- **THEN** every input is mapped from its configured trigger and the UI directs users to that trigger

#### Scenario: Incomplete setup
- **WHEN** a generated automatic workflow requires an unmapped run input
- **THEN** validation rejects it for correction without inventing a value

#### Scenario: Existing workflows
- **WHEN** the same objective previously produced a manual-input workflow
- **THEN** the automatic proposal has a distinct identity and preserves the published revision
