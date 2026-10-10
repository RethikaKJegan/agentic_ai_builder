# Spec Delta

## Purpose

Defines the canonical workflow document that every planner, UI integration, validator, tool selector, and runtime stage will exchange.

## ADDED Requirements

### Requirement: Workflow identity and revision
Every workflow document SHALL include a stable workflow ID, revision number, name, description, status, and metadata sufficient to identify its source and revision history.

#### Scenario: New workflow revision
- **WHEN** a user saves a changed workflow
- **THEN** the document SHALL retain its workflow ID and receive an identifiable revision

### Requirement: Typed workflow content
The document SHALL represent inputs, outputs, stakeholders, agents, tools, nodes, edges, conditions, approvals, execution policy, and error policy as typed fields.

#### Scenario: Missing required section
- **WHEN** a planner or client submits a document without required workflow content
- **THEN** schema validation SHALL reject it with the missing field identified

### Requirement: Typed node kinds
Nodes SHALL distinguish at least trigger, agent, tool/action, condition, approval, transform, and output behavior.

#### Scenario: Unsupported node kind
- **WHEN** a document contains an unknown node kind
- **THEN** validation SHALL reject the document before it can be approved or executed

### Requirement: Explicit graph references
Every edge SHALL reference existing node IDs, and conditions SHALL identify their possible outcomes and reachable targets.

#### Scenario: Broken edge
- **WHEN** an edge references a missing source or target
- **THEN** validation SHALL report the broken reference and reject the workflow

### Requirement: Layout independence
Visual layout information SHALL be optional presentation metadata and SHALL NOT determine execution order.

#### Scenario: Node repositioning
- **WHEN** layout coordinates change without changing graph references
- **THEN** workflow execution semantics SHALL remain unchanged
