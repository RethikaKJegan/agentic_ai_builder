# Spec Delta

## Purpose

Defines how natural-language business requirements become structured, reviewable workflow proposals without inventing critical business rules or unauthorized integrations.

## ADDED Requirements

### Requirement: Requirement decomposition
The planner SHALL identify objectives, stakeholders, responsibilities, tasks, dependencies, decisions, approvals, inputs, outputs, and required capabilities.

#### Scenario: Complete planning request
- **WHEN** a user submits a sufficiently detailed business process
- **THEN** the planner SHALL return a structured workflow proposal containing those identified elements

### Requirement: Agent versus deterministic classification
The planner SHALL assign AI agents only to tasks requiring reasoning and SHALL represent deterministic work as non-agent workflow nodes where appropriate.

#### Scenario: Deterministic operation
- **WHEN** a task only transfers data or invokes a fixed action
- **THEN** the planner SHALL be able to represent it without creating an AI agent

### Requirement: Uncertainty handling
The planner SHALL identify unresolved requirements and SHALL request clarification or mark them unresolved instead of silently inventing critical rules.

#### Scenario: Missing approval rule
- **WHEN** a requirement does not identify who approves a sensitive action
- **THEN** the planner SHALL flag the missing approval decision before execution can be approved

### Requirement: Structured output validation
Planner output SHALL be validated against the canonical workflow schema before it is presented as an editable workflow.

#### Scenario: Invalid planner output
- **WHEN** the model returns missing fields or invalid node references
- **THEN** the backend SHALL reject or repair the proposal through a controlled validation path and SHALL not execute it
