# Spec Delta

## Purpose

Provides a secure registry boundary that validates agent configurations, discovers approved tools, and assigns only authorized least-privilege tools to workflow agents.

## ADDED Requirements

### Requirement: Validate agent configurations

The registry SHALL validate every agent definition against `agent-contract-v1` before it can be selected for a workflow.

#### Scenario: Valid agent

- **WHEN** an agent has required identity, goal, instructions, model, capabilities, limits, and permissions
- **THEN** the registry accepts it and exposes its validated capabilities

#### Scenario: Over-privileged agent

- **WHEN** an agent requests permissions or limits outside workspace policy
- **THEN** the registry rejects it with a stable authorization error

### Requirement: Register approved tools

The registry SHALL store tool metadata, schemas, provider information, availability, risk, quota, cost, retry, timeout, credential-reference, and approval requirements according to `tool-contract-v1`.

#### Scenario: Complete connector definition

- **WHEN** an approved SMTP, Google, GitHub, Slack, weather, HTTP, or webhook tool is registered with valid metadata
- **THEN** the registry makes it discoverable to authorized workspace users

#### Scenario: Raw credential supplied

- **WHEN** a tool definition contains a raw secret instead of a credential reference
- **THEN** the registry rejects it and does not persist the secret

### Requirement: Match capabilities to tools

The registry SHALL return only tools whose capabilities, schemas, availability, workspace, permissions, risk, quota, and approval requirements satisfy the requested agent assignment.

#### Scenario: Eligible tool

- **WHEN** a planner capability has an available tool with matching input/output schema and authorized scope
- **THEN** the registry returns the tool assignment and its required approval metadata

#### Scenario: Unassigned or unavailable tool

- **WHEN** a requested tool is not assigned, unavailable, or outside the agent scope
- **THEN** the registry rejects the assignment with a stable error and no executable assignment

### Requirement: Enforce least privilege

The registry SHALL enforce subject, workspace, role, scope, destination, risk, quota, and approval policies before issuing an authorized assignment.

#### Scenario: Missing scope

- **WHEN** a builder requests a tool requiring a scope they do not possess
- **THEN** the registry returns a denied-operation error identifying the missing scope

#### Scenario: Allowlisted destination

- **WHEN** a connector destination is outside the workspace allowlist
- **THEN** the registry denies the assignment before runtime execution

### Requirement: Publish downstream-safe metadata

The registry SHALL publish metadata and assignments without raw credentials and with contract versions, authorization state, correlation IDs, and approval requirements.

#### Scenario: Consumer receives assignment

- **WHEN** a tool assignment is authorized
- **THEN** Harihar can display its safe metadata and Rethika can consume its authorization reference

#### Scenario: Authorization changes

- **WHEN** a tool becomes unavailable or a scope is revoked
- **THEN** new assignments are denied and the change is traceable to the affected version or request
