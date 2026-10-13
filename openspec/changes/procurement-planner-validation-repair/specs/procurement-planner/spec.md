## ADDED Requirements
### Requirement: Currency labelled limits
The planner SHALL normalize a purchasing-limit currency label only when it matches the project's comparison currency and SHALL request a bare decimal in model output.
#### Scenario: Matching label
- **WHEN** the model emits a limit labelled with the configured comparison currency
- **THEN** the numeric limit is preserved and the formatting label is removed
#### Scenario: Conflicting currency
- **WHEN** the model emits a different currency label
- **THEN** setup rejects the limit without silently converting it
### Requirement: Bounded grounded setup
Procurement planning SHALL derive bounded ranges from the selected discovered table and retain its actual column mappings.
#### Scenario: Full worksheet range
- **WHEN** a generated source uses the discovered full worksheet capacity
- **THEN** setup restricts it to the existing 100-data-row bound without expanding authorized columns
### Requirement: Precise setup errors
The planner SHALL retain privacy-safe validation codes rather than label every failure as a mapping error.
#### Scenario: Invalid Phase 2 policy
- **WHEN** a Phase 2 policy remains invalid after correction
- **THEN** the failure exposes its policy validation code without raw model output
