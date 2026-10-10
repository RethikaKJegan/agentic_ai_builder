# Spec Delta

## Purpose

Defines workflow revision states, run lifecycle states, event correlation, idempotency references, and legal state transitions shared by the UI and runtime.

## ADDED Requirements

### Requirement: Workflow revision lifecycle
Workflow revisions SHALL use explicit states for draft, validating, validation_failed, validated, approved, published, and archived transitions.

#### Scenario: Invalid revision
- **WHEN** validation fails for a draft revision
- **THEN** the revision SHALL enter `validation_failed` and SHALL not become executable

### Requirement: Run lifecycle
Runs SHALL expose explicit states for queued, running, paused_for_approval, completed, failed, rejected, cancelled, and blocked.

#### Scenario: Approval pause
- **WHEN** execution reaches an approval gate
- **THEN** the run SHALL enter `paused_for_approval` and SHALL expose an approval reference

### Requirement: Correlated run events
Every run event SHALL include a run ID, workflow ID, workflow version, event ID, timestamp, actor or source, and safe event details.

#### Scenario: Tool event
- **WHEN** a tool starts or finishes
- **THEN** the event SHALL be associated with the correct run and workflow revision

### Requirement: Idempotent execution requests
External execution requests SHALL accept an idempotency key and SHALL not create duplicate side effects for a repeated key within its retention period.

#### Scenario: Repeated execute request
- **WHEN** the UI retries an execute request with the same idempotency key
- **THEN** the API SHALL return the existing run or result instead of starting a duplicate side effect
