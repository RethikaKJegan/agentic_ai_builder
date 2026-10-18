## ADDED Requirements
### Requirement: Automatic KG-backed workflow planning
A single prompt submission SHALL retrieve relevant owned KG candidates and allow
the existing planner to select up to four execution datasets without a mandatory
user source-selection step. Retrieval SHALL bound candidate metadata, preserve
executable join constraints and pin the selected sources and relevant semantics.
#### Scenario: Multiple metadata matches
- **WHEN** several datasets match a prompt
- **THEN** a bounded candidate catalog is provided to the planner instead of requiring manual source selection
#### Scenario: Saved proposal
- **WHEN** generation and save succeed
- **THEN** the workflow editor opens without another source-choice or review-button click
#### Scenario: Existing constraints
- **WHEN** the planner proposes an unavailable source, unsupported join or unapproved action
- **THEN** existing validation and approval controls continue to apply
