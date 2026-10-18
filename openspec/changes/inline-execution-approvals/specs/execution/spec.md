## ADDED Requirements
### Requirement: Decide pending approvals in Execution
Execution SHALL expose existing approval controls for pending approvals matching the selected paused run and revision, and refresh the trace after a decision. Existing server permissions and database review requirements SHALL remain authoritative.

#### Scenario: Approve a Google action
- **WHEN** the selected run pauses at a matching spreadsheet, email or meeting approval
- **THEN** Execution displays its gate label and permitted Approve/Reject controls without navigation
- **AND** a decision submits the exact approval and workflow revision to the existing endpoint

#### Scenario: Historical or mismatched approval
- **WHEN** a run is terminal or an approval belongs to another workflow or revision
- **THEN** Execution does not expose a decision control for that approval
