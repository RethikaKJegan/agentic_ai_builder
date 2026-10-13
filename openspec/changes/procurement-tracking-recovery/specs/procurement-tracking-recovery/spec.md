## ADDED Requirements

### Requirement: Safe failure diagnostics
The extension SHALL persist only bounded diagnostic categories and secret-checked messages for failed effects, preserving unknown state and excluding complete provider bodies, URLs, headers and credentials.

#### Scenario: HTTP rejection
- **WHEN** a provider request returns HTTP 400
- **THEN** the journal retains the status category while the effect remains frozen

### Requirement: Operator requested tracking retry
The service SHALL allow a bounded fresh tracking attempt only after an authenticated approver identifies the exact failed run, no returned resource ID is recorded, and either an operator absence report or a journal-confirmed HTTP 400 rejection exists. The original intent SHALL remain preserved and the new write SHALL pass through a fresh action gate. Spreadsheet-level and sheet-level ownership metadata SHALL be placed in their matching request containers.

#### Scenario: Known returned resource
- **WHEN** the previous create returned a spreadsheet ID
- **THEN** absence-based retry is rejected and read-only resource reconciliation is required
