# Spec Delta

## Purpose

Defines the contributor-aware handoff process that tells each named person what to do, what they depend on, and what previous contributors must hand over before work continues.

## ADDED Requirements

### Requirement: Contributor identification
The project workflow SHALL recognize the names Suprajha, Aravind, Harihar, and Rethika when a contributor explicitly identifies themselves.

#### Scenario: Suprajha joins
- **WHEN** a user says “I am Suprajha”
- **THEN** the response SHALL show Suprajha’s responsibilities, inputs, deliverables, dependencies, verification steps, and current handoff status

### Requirement: Dependency-aware onboarding
Contributor onboarding SHALL identify completed prerequisites, missing prerequisites, upstream owners, downstream consumers, and contract versions relevant to that contributor.

#### Scenario: Aravind joins after Suprajha
- **WHEN** Aravind identifies himself after Suprajha’s work
- **THEN** the response SHALL show Suprajha’s delivered planner output, unresolved items, defects, and the exact planner contract Aravind must consume

### Requirement: Defect and change handoff
Each contributor handoff SHALL list known incorrect implementations, required fixes, open decisions, affected files or contracts, and the owner responsible for resolving each item.

#### Scenario: Upstream defect
- **WHEN** Suprajha’s output violates the workflow schema
- **THEN** Aravind’s handoff SHALL identify the violation, block dependent work when necessary, and notify Suprajha or the shared-contract owners

### Requirement: Completion record
A contributor SHALL record completed work, verification evidence, changed contracts, known limitations, and next-owner actions before their segment is considered complete.

#### Scenario: Segment completion
- **WHEN** Suprajha completes the planning segment
- **THEN** the handoff record SHALL contain test or validation evidence and the inputs required by Aravind, Harihar, and Rethika

### Requirement: Full accumulated context
When Rethika joins, the handoff response SHALL include the accumulated contract versions, completed work, defects, dependencies, and integration notes from all earlier segments.

#### Scenario: Rethika joins last
- **WHEN** a user says “I am Rethika”
- **THEN** the response SHALL show the complete upstream context needed to execute and observe the approved workflow

### Requirement: No implicit implementation authorization
Contributor onboarding SHALL explain tasks and status but SHALL NOT modify code or apply changes unless the contributor explicitly requests implementation through the approved workflow.

#### Scenario: Onboarding only
- **WHEN** a contributor identifies themselves without asking to implement
- **THEN** the system SHALL provide the handoff briefing and wait for an explicit implementation request
