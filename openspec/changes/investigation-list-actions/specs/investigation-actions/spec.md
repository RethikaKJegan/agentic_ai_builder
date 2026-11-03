## ADDED Requirements

### Requirement: Persistent list actions
Owners with appropriate workflow permissions SHALL rename and delete investigations through a three-dot list menu without changing immutable execution plans or company records.

#### Scenario: Rename
- **WHEN** an authorized owner saves a valid display name
- **THEN** the list shows that name after reload and preserves the original objective

#### Scenario: Delete
- **WHEN** an authorized owner confirms deletion of an idle workflow
- **THEN** it disappears from the list and cannot start new runs
- **AND** execution history remains retained internally

#### Scenario: Active workflow
- **WHEN** deletion targets a workflow with queued or running work
- **THEN** deletion is rejected without changing its visibility
