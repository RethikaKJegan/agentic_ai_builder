## ADDED Requirements
### Requirement: Grounded interpretation
The backend SHALL resolve supported questions using an authorized saved ontology version, aliases and valid mapping IDs, with deterministic fallback and validated optional model interpretation.
#### Scenario: Engine complaint lookup
- **WHEN** a caller asks for service issues for a motor with a serial
- **THEN** the plan selects saved complaint mappings and an exact serial filter without reading company rows during preview
### Requirement: Complete dependency closure
The resolver SHALL traverse required dependencies with cycles and registered conditional predicates, reporting missing providers or budget overflow explicitly.
#### Scenario: Missing policy
- **WHEN** a warranty request lacks an applicable pinned policy selection
- **THEN** policy applicability and conditional coverage requirements remain unresolved
### Requirement: Safe read execution
The backend SHALL execute only server-owned, version-pinned read plans with current authorization, source stamps, native references and bounded output.
#### Scenario: Changed metadata
- **WHEN** metadata changes between preview and execution
- **THEN** execution is rejected before source reads
### Requirement: Evidence and terminal access
The backend SHALL expose preview, execution and inspection through authenticated routes and the same-service terminal interface with source provenance, conversion issues and completeness.
#### Scenario: Shared serial
- **WHEN** two source records share a serial
- **THEN** they remain separate source-qualified records with candidate association and unresolved physical identity
