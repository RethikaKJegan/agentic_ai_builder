## ADDED Requirements
### Requirement: Scoped memory and recovery
The system SHALL derive bounded working context from persisted run state and reuse only validated, fresh, version-compatible, workspace-scoped experiences as untrusted strategy hints. Recovery SHALL preserve immutable execution pins, usage, audit and effect identity and SHALL invalidate only dependency descendants. Unknown external outcomes SHALL require reconciliation rather than automatic replay.

#### Scenario: Interrupted read-only composition
- **WHEN** a read-only composition is interrupted after a specialist checkpoint
- **THEN** authorized recovery preserves unaffected completed specialists and rechecks current execution authority before continuation

### Requirement: Reusable client packages
The system SHALL compile validated versioned client knowledge configuration using the existing capability factory, Registry, delegation and execution engine.

#### Scenario: Retail fixture
- **WHEN** an isolated inventory package requests a threshold summary
- **THEN** mapped stock evidence and deterministic threshold outcomes flow through temporary specialists and the existing runtime without company writes
