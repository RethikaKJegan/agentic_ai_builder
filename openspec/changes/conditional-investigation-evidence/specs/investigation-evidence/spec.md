## ADDED Requirements
### Requirement: Conditional analysis preserves the user's evidence conditions
The evaluator SHALL preserve evidence-conditional wording when decomposing and reassessing requirements. It SHALL verify evaluation and abstention using valid receipts and explicit limitations when a requested comparison is unsupported. It SHALL retain blocking gaps for unsupported unconditional or exhaustive outcomes. External follow-up SHALL still require a coherent verified assessment and normal approval.

#### Scenario: Comparisons only where supported
- **WHEN** the request permits comparisons only where units are comparable and returned evidence does not establish comparability
- **THEN** the assessment verifies evaluation and abstention using actual source receipts and discloses the limitation
- **AND** it may select reviewed delivery of those limited findings without claiming numerical differences

#### Scenario: Unconditional calculation or exhaustive analysis
- **WHEN** the objective requires an unconditional numerical conclusion or exhaustive row-level comparison and the necessary evidence is missing
- **THEN** the assessment retains a blocking gap and does not permit an external action as if the objective were verified

### Requirement: Inconsistent delivery decisions receive bounded correction
The runtime SHALL reject external execution when the assessment is ineligible and allow at most one budgeted reassessment with explicit feedback. It SHALL NOT change evidence, eligibility or approval to make a rejected action execute.

#### Scenario: Conditional assessment is corrected
- **WHEN** an evaluator selects external delivery while completion_eligible is false
- **THEN** no connector runs and one correction is offered
- **AND** a second inconsistent selection remains blocked
