## ADDED Requirements
### Requirement: Evidence-bound versioned knowledge graph
The application SHALL expose owned database/schema/dataset/field containment and
reviewable business entity mappings without granting execution authority.

#### Scenario: Metadata changes after confirmation
- **WHEN** a mapping's structural evidence changes
- **THEN** its saved review is marked needs-review and stale edits are rejected

#### Scenario: Existing queries consume the graph
- **WHEN** the v2 view and mapping controls are used
- **THEN** v1 remains compatible and changed revisions invalidate old query plans

#### Scenario: Relationship confidence is displayed
- **WHEN** a relationship is selected
- **THEN** declared constraints, metadata uniqueness, user decisions and unknown
  direction/cardinality/value overlap are distinguished without guessed probabilities
