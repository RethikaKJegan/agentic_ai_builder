## ADDED Requirements
### Requirement: Owned metadata retrieval
The system SHALL index only saved metadata owned by the current workspace subject,
search it before planning, and return reasons, bounded candidates and coverage.
#### Scenario: Large catalog
- WHEN the catalog contains more than 64 datasets
- THEN retrieval returns relevant candidates without sending the full catalog to the model.
### Requirement: Explicit ambiguity and freshness
The system SHALL require source selection for competing equally ranked sources
and reject a preview revision changed before generation.
#### Scenario: Metadata changes after preview
- WHEN a submitted preview revision differs from current saved metadata
- THEN generation fails with a safe instruction to refresh the preview.
### Requirement: Relationship authority
The system SHALL expand executable paths only through declared or accepted
technical relationships; semantic labels SHALL NOT confer query or write grants.
#### Scenario: Suggested relationship
- WHEN only a suggested relationship connects sources
- THEN the preview reports the missing usable path and does not silently grant a join.
### Requirement: Visible knowledge graph context
The UI SHALL display source reasons, fields, relationship paths and configured
tools before generation, and SHALL call the business graph Knowledge graph.
#### Scenario: User previews a prompt
- WHEN the user requests source preview
- THEN the UI shows current metadata context without executing database or Google actions.
