## Purpose

Provide an authenticated, evidence-backed catalogue of connected enterprise sources and bounded data profiles, with incremental change tracking.

## ADDED Requirements

### Requirement: Source capabilities and bounded synchronization
The system SHALL expose each connector's supported discovery, pagination, incremental synchronization and change-detection capabilities. Collection SHALL respect source scope, rate limits, continuation state and bounded retries without publishing obsolete partial results as complete.

#### Scenario: Rate-limited paginated source
- **WHEN** a source rate-limits collection after a page
- **THEN** collection preserves its checkpoint, honors retry limits and exposes incomplete coverage until collection completes

#### Scenario: Unsupported source capability
- **WHEN** a connector lacks incremental synchronization
- **THEN** its capability response declares this limitation and uses bounded scheduled discovery without claiming incremental source reads

### Requirement: Traceable metadata catalogue
The system SHALL catalogue source schemas, datasets, fields, types, descriptions, keys, constraints, lineage, freshness, ownership and accessible permissions with stable identifiers. Unknown or inaccessible metadata SHALL be labelled unavailable rather than invented.

#### Scenario: Inaccessible permission details
- **WHEN** the connector can read a table but cannot enumerate its grants
- **THEN** the catalogue records the effective access scope and marks grant enumeration unavailable

### Requirement: Bounded value profiling
The system SHALL calculate null rates, uniqueness, bounded distributions, overlaps, referential consistency and anomaly findings within authorized source scope. Each result SHALL include sample or population basis, coverage, time, source revision and method. Findings SHALL remain statistical evidence rather than business facts.

#### Scenario: Partial sample
- **WHEN** a profile examines a bounded sample containing missing values and unmatched reference keys
- **THEN** results use the actual denominators and identify sampled null rates and referential consistency without claiming population completeness

#### Scenario: No authorized record access
- **WHEN** source access does not permit record profiling
- **THEN** metadata remains available within its scope and value statistics remain unavailable

### Requirement: Incremental metadata and evidence changes
The system SHALL detect new sources, schema changes, changed keys and possible renames, retaining affected stable identities where evidence verifies continuity. It SHALL refresh changed components and invalidate dependent mappings. Ambiguous renames and omissions from incomplete samples SHALL require further evidence.

#### Scenario: One changed key
- **WHEN** one dataset changes its primary key while unrelated source evidence remains identical
- **THEN** affected mappings are revalidated while unrelated approved mappings retain their evidence identity

#### Scenario: Ambiguous rename
- **WHEN** a field disappears and a similarly named field appears without reliable continuity evidence
- **THEN** the system presents a possible rename without silently transferring approvals
