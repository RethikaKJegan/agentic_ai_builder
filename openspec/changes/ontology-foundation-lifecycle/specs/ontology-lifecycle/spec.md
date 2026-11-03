## Purpose

Publish approved ontology versions and serve authorized task context with traceable dependencies, correction impact and controlled workflow revalidation.

## ADDED Requirements

### Requirement: Source-backed business object exploration
The system SHALL provide authorized, read-only record exploration through approved current definitions, with native source identity, safe field projection, bounded pagination and provenance. Expansion SHALL distinguish source references from candidate associations without granting join or execution authority. Existing definition-only task selection SHALL remain separate.

#### Scenario: Concept box opens underlying information
- **WHEN** an authorized user selects a source-backed concept and browses its records
- **THEN** the UI shows readable definitions and permitted source values with native record identity and explicit missing/unavailable states

#### Scenario: Ambiguous serial association
- **WHEN** a ticket serial matches invoice records under multiple companies
- **THEN** the explorer retains separate candidate records and does not assert physical engine identity or current ownership

#### Scenario: Stale or revoked record access
- **WHEN** source access, approved evidence or request scope changes during a read
- **THEN** the response is rejected or discarded without exposing stale or restricted values

#### Scenario: Safe bounded record projection
- **WHEN** a source account includes passwords or unsupported nested values
- **THEN** the explorer projects only permitted supported fields, excludes secrets at the server and reports bounded incomplete results explicitly

### Requirement: Immutable approved publication
The system SHALL publish immutable ontology versions containing approved concepts, mappings, constraints, relationships, evidence and validation results. Publication SHALL atomically pin source and calibration revisions and reject stale evidence or blocking validation errors. Repeated identical publication requests SHALL be idempotent.

#### Scenario: Stale publication
- **WHEN** a source changes after validation but before publication
- **THEN** publication fails with a conflict and the previously published version remains intact

### Requirement: Authenticated versioned access and export
The system SHALL provide authenticated versioned APIs and export for approved concepts, mappings, relationships and ontology versions, supporting lookups by concept, source field, entity ID and relationship type. Responses SHALL include evidence references, validation status and ontology version and enforce current tenant and source permissions, including historical reads.

#### Scenario: Revoked source access
- **WHEN** a caller requests a historical ontology version after source access is revoked
- **THEN** the response does not expose the revoked source or its derived restricted information

### Requirement: Task-specific dependency resolution
The system SHALL resolve a bounded task-relevant subset across all three layers, including required attributes, constraints, mappings and relationship dependencies. It SHALL return a version-pinned context manifest identifying consumed evidence and excluded unresolved candidates. Overflow or missing required dependencies SHALL be explicit.

#### Scenario: Sales task subset
- **WHEN** an authorized task needs a customer concept and its order relationship
- **THEN** context includes the required common, Sales and organization definitions and constraints without unrelated enterprise concepts

### Requirement: Correction impact and revalidation
A verified correction or source change SHALL identify affected mappings, caches, relationships and dependent workflows. The system SHALL invalidate affected current context, retain historical manifests, revalidate dependencies and prevent affected workflows from silently consuming superseded interpretations.

#### Scenario: Corrected relationship used by a workflow
- **WHEN** a reviewed relationship is corrected after a workflow consumed it
- **THEN** the system can trace the run to its ontology version and source evidence, invalidates affected cached context and records the workflow revalidation result

### Requirement: Controlled eligible replay
The system SHALL identify workflow replay eligibility following correction, retain an auditable replay decision, and use existing execution authorization, approval and idempotency controls for replay. Completed external writes and unknown outcomes SHALL require reconciliation before repeat execution.

#### Scenario: Prior external write outcome unknown
- **WHEN** a correction affects a run whose external write outcome is unknown
- **THEN** automatic replay is blocked pending reconciliation and the reason is recorded

### Requirement: End-to-end Simpsons acceptance
Foundation completion SHALL require a demonstration using the existing Simpsons connection: catalogue, bounded profiles, layered mappings, review, approved publication, authorized subset retrieval and correction lineage. Drift and replay fault scenarios SHALL additionally be verified in isolated sources without altering company schemas or fabricating expert approvals.

#### Scenario: Incomplete business definitions
- **WHEN** Simpsons metadata is available but a required business definition lacks expert validation
- **THEN** the acceptance report identifies the unresolved mapping and does not claim full business validation
