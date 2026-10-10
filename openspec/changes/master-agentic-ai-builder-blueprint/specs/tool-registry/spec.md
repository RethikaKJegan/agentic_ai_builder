# Spec Delta

## Purpose

Defines the approved capability-to-tool catalogue used to select safe, available, and appropriately authorized connectors for workflow execution.

## ADDED Requirements

### Requirement: Complete registry entries
Each registered tool SHALL declare its tool ID, provider, capability, input/output schemas, authentication needs, permissions, availability, rate limits, risk, cost, retry policy, timeout, and approval requirement.

#### Scenario: Incomplete tool
- **WHEN** an administrator attempts to enable a tool missing a required registry field
- **THEN** the system SHALL keep the tool unavailable and report the missing metadata

### Requirement: Capability-based selection
The planner SHALL request business capabilities and the selection layer SHALL map them only to compatible approved tools.

#### Scenario: Compatible candidate
- **WHEN** a workflow requires `send_email`
- **THEN** the selector SHALL return enabled email tools whose schemas and permissions support that capability

### Requirement: Availability and risk filtering
Tool selection SHALL consider authentication readiness, permissions, quotas, cost, risk, reliability, and free-tier constraints.

#### Scenario: Unavailable connector
- **WHEN** a candidate lacks valid authorization or exceeds an applicable quota
- **THEN** the selector SHALL exclude it and explain the reason

### Requirement: Restricted external actions
The system SHALL prevent unrestricted arbitrary API execution and SHALL require allowlisted destinations and explicit authorization for external writes.

#### Scenario: Unallowlisted destination
- **WHEN** a workflow requests an external endpoint outside the approved connector policy
- **THEN** execution SHALL be denied before the request is sent
