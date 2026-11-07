## ADDED Requirements

### Requirement: Evidence coverage is measured against supplied sources
The audit SHALL enumerate source models and collections and distinguish mapped,
unmapped, code-only and unsupported execution coverage without asserting completeness
from compilation alone.

#### Scenario: A question uses terms present only in a saved rule
- **WHEN** an authenticated Subway user requests evidence matching that rule
- **THEN** pinned retrieval returns the relevant source-cited rule
- **AND** no foreign workspace evidence or additional execution authority is introduced
