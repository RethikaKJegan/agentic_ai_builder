## ADDED Requirements

### Requirement: Configured HTTP execution returns durable admission
Configured combined-mode applications SHALL defer runtime advancement to their
existing worker and SHALL return the persisted run identity before model work.

#### Scenario: Slow model or connector
- **WHEN** a configured combined-mode API admits a workflow
- **THEN** it returns the durable run without invoking its runner inline
- **AND** the existing worker retains ownership and approval enforcement

### Requirement: Lost execution response can be recovered read-only
Composition views SHALL discover only the latest authorized run of that workflow
when no explicit run ID is supplied.

#### Scenario: Browser loses the admitted run response
- **WHEN** the operator refreshes the saved composition
- **THEN** the existing run and actual task states are returned
- **AND** no new run or provider action is issued
