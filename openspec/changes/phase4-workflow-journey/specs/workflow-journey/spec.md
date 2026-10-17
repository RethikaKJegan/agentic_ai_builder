## ADDED Requirements

### Requirement: Guided workflow lifecycle
The editor SHALL display lifecycle progress and prerequisites derived from persisted revision and release state, and SHALL mark unsupported simulation unavailable.

#### Scenario: New draft
- **WHEN** a generated draft is reviewed
- **THEN** the user sees its actual goal, sources, trigger, steps, responsibilities, tools, outputs, approval points and missing configuration before explicitly opening the editor
- **AND** no approval, publication or activation is implied

### Requirement: Separate design and execution
The editor SHALL separate editable design, agent hierarchy and read-only exact-revision execution without losing dirty draft edits.

#### Scenario: Historical run
- **WHEN** a user selects a run from an older revision
- **THEN** the graph uses that run's exact workflow revision and recorded event identity/order
- **AND** a missing revision displays a failure instead of an unrelated graph
- **AND** returning to Design preserves unsaved edits

### Requirement: Accessible graph editing
The editor SHALL expose dependency-ordered steps, graph diagnostics and keyboard-accessible editing controls while retaining React Flow and supported layout persistence.

#### Scenario: Mobile branch edit
- **WHEN** a user inspects a condition on a small screen
- **THEN** its declared branch outcomes and errors are readable and connections can be edited through labeled controls
- **AND** server validation remains authoritative
