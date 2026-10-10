# tool-contract-v1 Specification

## Purpose
Defines the registry contract for mapping business capabilities to authorized, observable, and bounded connector tools.

## Requirements

### Requirement: Complete tool metadata
Each tool SHALL declare a stable ID, provider, capability, description, input schema, output schema, authentication requirements, permissions, availability, risk, rate limits, retry policy, timeout, cost, and approval requirement.

#### Scenario: Incomplete registry entry
- **WHEN** a tool is registered without required metadata
- **THEN** the system SHALL keep it unavailable and identify the missing fields

### Requirement: Capability-based resolution
Tools SHALL be selected by matching requested business capabilities to approved registry entries rather than by allowing the planner to invent connector identifiers or endpoints.

#### Scenario: Capability match
- **WHEN** a workflow requests `send_email`
- **THEN** the registry SHALL return only enabled tools whose declared schemas support that capability

### Requirement: Authorization and availability filtering
Tool selection SHALL exclude tools that lack required credentials, permissions, quota, availability, or policy approval.

#### Scenario: Unconfigured connector
- **WHEN** a candidate connector needs authentication that is not configured
- **THEN** it SHALL be excluded and the reason SHALL be available to the workflow review

### Requirement: Restricted destinations
HTTP or webhook tools SHALL use approved destinations and SHALL reject arbitrary unallowlisted external writes.

#### Scenario: Unallowlisted endpoint
- **WHEN** a workflow requests an endpoint outside the approved destination policy
- **THEN** the tool call SHALL be denied before network execution

### Requirement: Least-privilege assignment
The runtime tool set for an agent SHALL contain only the tools explicitly selected and authorized for that agent’s workflow role.

#### Scenario: Tool isolation
- **WHEN** two agents in the same workflow have different tool assignments
- **THEN** each agent SHALL be unable to call the other agent’s unassigned tools
