## ADDED Requirements

### Requirement: Prompt-owned destinations
The planner SHALL generate per-workflow spreadsheet destinations from the setup prompt without requiring per-spreadsheet backend configuration.

#### Scenario: User selects another spreadsheet
- **WHEN** a user supplies another accessible spreadsheet in a new setup prompt
- **THEN** its target list is saved in that workflow revision
- **AND** no per-spreadsheet environment edit is required

### Requirement: Reviewed resource binding
The runtime SHALL bind writes to the target settings of the exact reviewed workflow revision and preserve existing Registry, approval and budget controls.

#### Scenario: Incoming data attempts to change the destination
- **WHEN** a task requests a spreadsheet or column outside its reviewed workflow targets
- **THEN** no write occurs

#### Scenario: No reviewed targets
- **WHEN** neither workflow metadata nor a legacy operator target list configures destinations
- **THEN** publication or connector execution fails closed

### Requirement: Visible access review
The editor SHALL display spreadsheet IDs, table ranges, writable columns and record-creation permission before publication.

#### Scenario: Workflow is reviewed
- **WHEN** a generated draft declares sheet write targets
- **THEN** the editor shows the target settings and identifies publication as approving that access
