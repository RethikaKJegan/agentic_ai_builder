## ADDED Requirements

### Requirement: Durable scoped cases
The backend SHALL persist version-pinned cases, independent stage states, provenance,
command receipts and external waits in the existing application store.

#### Scenario: Restart and duplicate commands
- **WHEN** the service restarts and a completed command is retried
- **THEN** the pinned case and command result survive without replaying effects

### Requirement: Qualified evidence and execution
The backend SHALL prefer actual evidence, deterministic derivation, grounded inference
and explicit synthetic assumptions in that order, retaining conflicts and limitations.

#### Scenario: Missing inspection evidence
- **WHEN** analytical continuation uses a provisional inspection hypothesis
- **THEN** the physical inspection remains unverified and cannot grant authorization

### Requirement: Existing runtime authority
The backend SHALL execute capabilities through the existing composition, master-child
and CrewAI runtime under existing workflow approval and Registry checks.

#### Scenario: Unapproved external action
- **WHEN** a stage requests execution without an approved workflow revision
- **THEN** existing execution authorization denies the action
