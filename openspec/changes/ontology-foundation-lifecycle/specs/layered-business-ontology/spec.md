## Purpose

Represent reusable, domain and organization business knowledge as a connected typed graph with stable identity and explicit evidence provenance.

## ADDED Requirements

### Requirement: Layered typed business graph
The system SHALL represent common, domain and organization concepts, typed attributes, relationships, constraints and source mappings with stable identifiers and versions. Domain coverage SHALL support Sales, Procurement, Finance and Customer Service; organization terminology, custom fields, approval hierarchies and rules SHALL map to relevant shared concepts.

#### Scenario: Organization term maps across layers
- **WHEN** an organization defines a custom customer term mapped to a Sales concept and a common party concept
- **THEN** the graph preserves all three identities, definitions and mapping provenance without replacing organization terminology

### Requirement: Evidence classification and provenance
The system SHALL distinguish observed facts, model inferences, statistical findings and unverified hypotheses. Relationships SHALL retain typed endpoints, evidence references, inference method, score availability, validation status, lineage and ontology version. Source constraints SHALL prove structural links only; business predicates SHALL require their own evidence.

#### Scenario: Foreign key without business definition
- **WHEN** a foreign key links two datasets but the business meaning is ambiguous
- **THEN** the structural relationship is source-backed and any proposed business predicate remains an inference or unresolved hypothesis

#### Scenario: Statistical correlation
- **WHEN** two fields correlate in a profile
- **THEN** the observation remains a statistical finding and does not become an approved business relationship solely because of correlation

### Requirement: Constraint and mapping consistency
The system SHALL validate typed attributes, endpoint existence, layer dependencies, mapping compatibility and supported business constraints before publication. Unsupported rule forms SHALL remain documented unresolved definitions rather than silently executable rules.

#### Scenario: Conflicting domain and organization constraint
- **WHEN** an organization mapping contradicts a required domain attribute type
- **THEN** validation reports both definitions and their provenance and blocks publication of the conflict

### Requirement: Stable identity and explicit merges
Concept identity SHALL be independent of display labels. Merging SHALL retain prior identifiers, source lineage and historical references through explicit redirects, reject incompatible merges or redirect cycles, and identify affected dependencies.

#### Scenario: Rename then merge
- **WHEN** an expert renames one concept and later merges a verified duplicate into it
- **THEN** the rename preserves identity and the merge resolves old identifiers while retaining their historical evidence

### Requirement: Relationship-specific cycle rules
The system SHALL allow cycles in ordinary business relationships and SHALL reject cycles only for predicates whose explicit rules require acyclicity or for merge redirect chains.

#### Scenario: Reciprocal business relationships
- **WHEN** two concepts reference each other through a predicate without an acyclic rule
- **THEN** both relationships are valid

#### Scenario: Cyclic approval hierarchy
- **WHEN** an approval hierarchy explicitly requires acyclicity and an edge closes a cycle
- **THEN** validation rejects that hierarchy with the offending rule identified
