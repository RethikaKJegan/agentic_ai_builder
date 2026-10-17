## ADDED Requirements
### Requirement: Evidence-backed metadata graph
The system SHALL build bounded versioned graphs from owned metadata snapshots,
preserve ordered declared foreign keys and label inferred relationships as proposals.
#### Scenario: Cross-source candidate
- **WHEN** compatible scalar identifier fields match across different connections
- **THEN** a proposal includes its evidence and makes no claim of value overlap or cardinality
### Requirement: Persistent review and descriptions
The system SHALL retain decisions only while their evidence fingerprint matches,
and require a current graph version for edits.
#### Scenario: Schema changes after review
- **WHEN** a reviewed field changes type or its source is disconnected
- **THEN** the old decision is not treated as a currently valid relationship
### Requirement: Owned durable graph builds
The system SHALL enforce owner/workspace permissions and recover expired build leases.
#### Scenario: Inputs change while building
- **WHEN** metadata changes during a graph build
- **THEN** the obsolete build cannot publish as current
### Requirement: Inspectable relationships
The UI SHALL show source revisions, declared versus suggested evidence, review controls,
manual business descriptions, loading and error states.
#### Scenario: Review proposal
- **WHEN** an authorized user accepts or rejects a current proposal
- **THEN** the decision persists across reloads and is visible with its evidence
