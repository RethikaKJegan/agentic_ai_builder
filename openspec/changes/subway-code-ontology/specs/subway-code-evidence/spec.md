## ADDED Requirements

### Requirement: Code-backed ontology preserves evidence and authority
Subway definitions SHALL cite exact hashed source excerpts with archive/member/line
provenance. Implemented behavior SHALL remain descriptive and non-executable;
commented or defective guards SHALL NOT be represented as verified enforcement.

#### Scenario: Model exists only in supplied code
- **WHEN** its collection is absent from restored source metadata
- **THEN** the ontology labels its data availability as unverified
- **AND** no source connection, executable join or fabricated records are created

### Requirement: Immutable revisions preserve existing workflows
The platform SHALL activate a new Subway ontology/package revision without rewriting
older versions or changing Simpsons definitions, data or authority.

#### Scenario: An older workflow runs after activation
- **WHEN** it references the original package revision
- **THEN** that immutable revision and its original read bindings remain available
