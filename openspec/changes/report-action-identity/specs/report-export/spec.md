## ADDED Requirements

### Requirement: A report belongs to one runtime action
A generated spreadsheet report SHALL use its workspace, workflow revision and
runtime action reference in its effect identity. A repeated action with the same
inputs SHALL reuse its verified receipt. Changed inputs for that same action
SHALL be rejected. A different run SHALL create a separate report even when it
shares a project and creation key. Permanent spreadsheet setup identity SHALL
remain unchanged. Existing receipts and uncertain writes SHALL be preserved.

#### Scenario: Repeated run with new findings
- **WHEN** a new run produces changed findings using the same report creation key
- **THEN** its approved report creates a distinct spreadsheet without conflicting with earlier receipts

#### Scenario: Repeated action
- **WHEN** the same action reference and identical report content are retried
- **THEN** its verified spreadsheet is reused without another creation

#### Scenario: Action content changed
- **WHEN** the same action reference carries different report content
- **THEN** the connector rejects the mismatch before any provider mutation
