## ADDED Requirements

### Requirement: Explicit alternative predicates survive planning
The system SHALL validate and pin bounded alternative predicates interpreted from the user objective. Every pinned category SHALL have a source read and SHALL be supplied to reporting. Generated queries SHALL preserve the exact pinned predicates before execution.

#### Scenario: Planner emits only one category
- **WHEN** intent contains multiple alternative filter branches and the planner supplies one query/read template
- **THEN** the server expands that template for every category and reporting receives every branch result

#### Scenario: Generated query omits a condition
- **WHEN** a query does not preserve its pinned branch filters
- **THEN** validation rejects it before source dispatch

#### Scenario: Existing workflow has no alternatives
- **WHEN** a saved selection or workflow has no pinned alternative predicates
- **THEN** existing query and workflow behavior is preserved
