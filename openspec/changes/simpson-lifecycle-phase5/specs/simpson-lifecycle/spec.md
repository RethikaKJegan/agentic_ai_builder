## ADDED Requirements

### Requirement: Versioned Simpson lifecycle
The backend SHALL execute the requested twelve stages using the existing Phase 4
process/case engine, provenance and Registry-authorized runtime.

#### Scenario: Replacement analysis
- **WHEN** a mapped complaint selects a replacement analysis path
- **THEN** twelve stage results retain real/generated provenance and pending physical activities

### Requirement: Bounded lifecycle driver
The backend SHALL drive existing commands within persisted command/time budgets,
stop at approval/event/input waits and preserve restart/retry safety.

#### Scenario: Approval wait
- **WHEN** an eligible stage creates an unapproved workflow
- **THEN** the driver stops without granting approval or repeating paid work

### Requirement: Analytical outcomes
The backend SHALL persist a stage-by-stage analytical report with pending actual
activities, conditionally skipped branches and original evidence references.

#### Scenario: Repair or warranty rejection
- **WHEN** replacement or corrective action is not applicable
- **THEN** those branches are skipped without recording physical completion
