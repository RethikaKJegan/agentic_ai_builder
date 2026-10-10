# Spec Delta

## Purpose

Defines the portable contract for runtime agents so each agent has an explicit responsibility, bounded access, and measurable execution policy.

## ADDED Requirements

### Requirement: Explicit agent identity
Every runtime agent SHALL declare an identifier, name, role, goal, instructions, model configuration, input schema, and output schema.

#### Scenario: Agent registration
- **WHEN** an agent is added to a workflow
- **THEN** the system SHALL reject it if any required identity or input/output field is missing

### Requirement: Least-privilege tools
An agent SHALL receive only the capabilities and tools explicitly assigned by the validated workflow.

#### Scenario: Unauthorized tool request
- **WHEN** an agent requests a tool outside its approved assignment
- **THEN** the runtime SHALL deny the request and record the authorization failure

### Requirement: Bounded agent execution
Every agent SHALL declare applicable call, token, retry, timeout, cost, and approval limits before execution.

#### Scenario: Limit reached
- **WHEN** an agent reaches a configured execution limit
- **THEN** the runtime SHALL stop or pause the agent according to the workflow failure and approval policy

### Requirement: Human approval policy
An agent SHALL be able to declare approval requirements for sensitive actions or outputs.

#### Scenario: Approval-required action
- **WHEN** an agent reaches an action marked as requiring approval
- **THEN** the workflow SHALL pause until an authorized human decision is recorded
