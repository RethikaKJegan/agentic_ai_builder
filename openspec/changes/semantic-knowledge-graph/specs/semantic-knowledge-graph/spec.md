## ADDED Requirements
### Requirement: Evidence-backed semantic proposals
The system SHALL propose predicates and direction using current structural
relationships and descriptions, validate cited evidence IDs, preserve original
field mappings and label model proposals inferred or ambiguous, never verified.
#### Scenario: Unsupported business meaning
- WHEN schema evidence cannot establish a business interpretation
- THEN the edge remains ambiguous and requests review rather than inventing a verb.
### Requirement: Reviewed semantics and freshness
The system SHALL preserve unchanged reviews and mark changed evidence as needing
review, independently of technical join authority.
#### Scenario: Changed source schema
- WHEN a metadata refresh changes supporting evidence
- THEN stale semantics are excluded from planning until regenerated or reviewed.
### Requirement: Actual records
The system SHALL display only records returned by validated read queries with
bounded expansion and source/query provenance; unavailable keys or ambiguous
record identity SHALL be reported explicitly.
#### Scenario: Requested customer record
- WHEN an authorized user supplies a dataset, scalar identity field and value
- THEN the KG displays matching actual records and only supported observed links.
### Requirement: One Knowledge graph before planning
The UI SHALL expose one KG instead of separate structural graph navigation, and
workflow planning SHALL retrieve relevant semantic context and configured tools
before generating workflow proposals.
#### Scenario: Customer tracking workflow
- WHEN the prompt names a reviewed customer concept
- THEN retrieval narrows the available datasets and preserves source reasons and semantic evidence.
