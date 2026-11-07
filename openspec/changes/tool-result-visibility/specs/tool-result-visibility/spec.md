## ADDED Requirements

### Requirement: Display actual tool execution evidence
The existing inspector SHALL display the persisted selected tool and actual read
result metadata without classifying a database read as an empty external-write receipt.

#### Scenario: Database read returned records
- **WHEN** a connected task has recorded source records
- **THEN** its view retains those records and reports the tool, count and collections
- **AND** rendering performs no source read or execution replay

#### Scenario: Database read found no matches
- **WHEN** the saved read returned zero records
- **THEN** the view explicitly reports no matching records
- **AND** does not fabricate rows or hide the zero-result outcome
