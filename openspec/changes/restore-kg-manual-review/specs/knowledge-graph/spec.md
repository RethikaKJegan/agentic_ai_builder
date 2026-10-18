## ADDED Requirements
### Requirement: Manual semantic correction in Inspect
The Inspect sidebar SHALL allow authorized owners to edit a selected relationship's
meaning and direction and confirm, reject or reset its business review through the
existing semantic review API. Stale graphs and read-only sessions SHALL disable
review. Technical relationship permissions SHALL remain independent.
#### Scenario: Resolve an ambiguous or needs-review edge
- **WHEN** an owner supplies a meaningful predicate and confirms its direction
- **THEN** the request includes the current graph revision and selected relationship ID and the returned graph is rendered
#### Scenario: Read-only or stale evidence
- **WHEN** the graph is stale or the session cannot manage it
- **THEN** review controls cannot submit a change
