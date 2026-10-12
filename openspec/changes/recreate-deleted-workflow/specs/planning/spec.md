## ADDED Requirements

### Requirement: Fresh drafts after deletion
The system SHALL produce a fresh workflow identity when an identical planning request targets a deleted workflow.

#### Scenario: Same prompt after deletion
- **WHEN** the previous planned workflow has a deletion record
- **THEN** planning returns a draft under a replacement identity with matching agent references

#### Scenario: Repeated regeneration
- **WHEN** the replacement workflow has not been deleted
- **THEN** repeated planning returns the same replacement identity

#### Scenario: Historical preservation
- **WHEN** a deleted workflow is regenerated
- **THEN** its historical revisions and deletion record remain unchanged
