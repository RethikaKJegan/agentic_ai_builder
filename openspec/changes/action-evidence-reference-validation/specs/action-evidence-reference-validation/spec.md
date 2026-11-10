## ADDED Requirements

### Requirement: Explicit evidence dependency closure
Automatic-input planning SHALL materialize evidence references to existing distinct actions as graph dependencies before validation. Pinned evidence identities SHALL be preserved without adding action edges. Unknown references SHALL NOT be removed or treated as verified.

#### Scenario: Report cites an earlier query through another action
- **WHEN** a generated report cites an existing query action without declaring a direct dependency
- **THEN** that dependency is added and all existing graph, condition and approval checks apply

### Requirement: Bounded evidence correction
Evidence-reference validation SHALL run before compilation inside the existing bounded planning correction boundary and provide invalid references plus allowed dependency and pinned-evidence identities. Explicit plans SHALL remain strict.

#### Scenario: Model invents a reference
- **WHEN** a generated plan cites an unknown identity
- **THEN** one correction can replace it with genuine available evidence
- **AND** repeated invalid references fail without compiling or executing the workflow

#### Scenario: Evidence dependency creates a cycle
- **WHEN** adding an evidence dependency creates a graph cycle or requires a conditional action
- **THEN** the plan is rejected by existing graph validation
