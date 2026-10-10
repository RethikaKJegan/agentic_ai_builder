# Spec Delta

## Purpose

Defines the versioned workflow document that remains the single source of truth from natural-language planning through visual editing, validation, and execution.

## ADDED Requirements

### Requirement: Versioned workflow identity
Every workflow SHALL have an identifier, version, name, description, status, inputs, outputs, and audit metadata.

#### Scenario: Workflow revision
- **WHEN** a user saves an edited workflow
- **THEN** the system SHALL create or update a versioned workflow revision without losing the prior approved revision

### Requirement: Typed workflow nodes
The specification SHALL distinguish agents, deterministic actions, conditions, approvals, inputs, and outputs.

#### Scenario: Node validation
- **WHEN** a workflow contains an unsupported or untyped node
- **THEN** validation SHALL reject the workflow with an actionable error

### Requirement: Explicit graph semantics
Execution order SHALL be determined by edges, dependencies, and conditions rather than by visual node position.

#### Scenario: Node repositioning
- **WHEN** a user moves a node on the canvas without changing its edges
- **THEN** the execution order SHALL remain unchanged

### Requirement: Portable specification
The workflow specification SHALL remain independent of frontend graph-library and runtime-specific object structures.

#### Scenario: Runtime replacement
- **WHEN** the frontend or agent runtime implementation changes
- **THEN** the saved workflow contract SHALL remain readable and valid without requiring UI-generated executable code
