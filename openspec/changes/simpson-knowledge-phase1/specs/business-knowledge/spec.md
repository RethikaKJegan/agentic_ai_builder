## ADDED Requirements
### Requirement: Versioned connected business knowledge
The backend SHALL enrich populated Simpson modules using stable IDs and persist machine-readable mappings, identity, state, time, rule and dependency definitions in immutable owner-scoped versions.

#### Scenario: Repeated import
- **WHEN** an identical package import is retried with the same request key
- **THEN** the original version is returned without creating another revision

#### Scenario: Concurrent revision
- **WHEN** the requested base revision is no longer current
- **THEN** import fails without changing saved knowledge

### Requirement: Honest source semantics
The backend SHALL distinguish conceptual relationships, typed source references and candidate identity associations, and SHALL retain internal origin for configured conditions.

#### Scenario: Equal cross-source identifiers
- **WHEN** unrelated source records have equal-looking identifiers or serial numbers
- **THEN** they remain separate and any association reports its evidence and uncertainty

### Requirement: Backend inspection and compatibility
The backend SHALL expose saved knowledge and bounded diagnostics without frontend or model calls, preserve old versions and executable handlers, and prevent regeneration from discarding enrichment.

#### Scenario: Historical version
- **WHEN** an earlier version is inspected after import
- **THEN** its original content and graph bindings remain unchanged

#### Scenario: Regeneration conflict
- **WHEN** regenerated definitions conflict with protected knowledge
- **THEN** generation fails explicitly rather than erasing that knowledge
