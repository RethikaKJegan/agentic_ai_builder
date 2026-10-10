# Spec Delta

## Purpose

Defines the portable runtime-agent configuration that limits each agent to an explicit responsibility, capability set, tool set, and execution policy.

## ADDED Requirements

### Requirement: Complete agent identity
An agent definition SHALL include an ID, name, role, goal, instructions, model configuration, input schema, and output schema.

#### Scenario: Incomplete agent
- **WHEN** an agent is added without a required identity or schema field
- **THEN** the system SHALL reject the agent definition before workflow approval

### Requirement: Explicit capabilities and tools
An agent definition SHALL identify its required capabilities and explicitly assigned tools separately.

#### Scenario: Capability resolution
- **WHEN** a planner requests an agent capability
- **THEN** the system SHALL resolve it through the Tool Registry before assigning executable tools

### Requirement: Least-privilege permissions
An agent SHALL declare permissions and SHALL receive no capability or tool outside its validated assignment.

#### Scenario: Unauthorized request
- **WHEN** an agent requests an unassigned tool
- **THEN** the runtime SHALL deny the request and record the denial

### Requirement: Bounded execution policy
An agent definition SHALL support limits for model calls, tokens, tool calls, retries, duration, estimated cost, and sensitive-action approvals.

#### Scenario: Agent limit reached
- **WHEN** an agent exceeds a configured limit
- **THEN** execution SHALL stop or pause according to the workflow policy

### Requirement: Safe instruction data
Agent instructions SHALL not contain raw credentials, secrets, or unscoped permissions.

#### Scenario: Credential in instructions
- **WHEN** an agent definition contains a detected secret
- **THEN** validation SHALL reject or redact it before persistence
