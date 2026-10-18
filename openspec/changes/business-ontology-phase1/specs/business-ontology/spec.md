## ADDED Requirements

### Requirement: Reviewable business ontology
The system SHALL project business entities and named directed relationships from owned technical graph evidence. Reviews SHALL bind to ontology and source evidence, support label/direction correction and reset, preserve unchanged evidence, and never grant executable joins or permissions. Stale graphs SHALL reject edits. Existing graph consumers SHALL remain compatible.

#### Scenario: Review a predicate
- **WHEN** an authorized user confirms a predicate and direction using the current ontology revision
- **THEN** the review persists and source field pairs and evidence remain inspectable

#### Scenario: Supporting structure changes
- **WHEN** relevant source or entity evidence changes
- **THEN** the relationship requires renewed review and disconnected sources disappear

### Requirement: Automatic metadata refresh
The system SHALL expose owned per-connection automatic refresh controls, last/next check and failure state. The existing worker SHALL schedule due metadata-only profiles without duplicate active jobs, with bounded retry backoff. Unchanged automatic checks SHALL preserve metadata and graph revisions. Failed checks SHALL retain successful metadata.

#### Scenario: Automatic check finds no changes
- **WHEN** a due profile returns the same bounded structural metadata
- **THEN** freshness advances without rebuilding the graph or invalidating plans

#### Scenario: A due source changes or fails
- **WHEN** a due profile discovers a structural change or encounters an error
- **THEN** a change queues graph rebuilding and a failure preserves the previous snapshot with visible retry state

### Requirement: Inspectable ontology canvas
The UI SHALL show selectable entity nodes and labelled relationship edges, zoom/pan/fit, search and connection filters, evidence/review details, and visible build/freshness states on desktop and mobile.

#### Scenario: Inspect a cross-source relationship
- **WHEN** the user selects a relationship
- **THEN** both source datasets, exact linking fields, semantic review and technical eligibility are displayed separately
