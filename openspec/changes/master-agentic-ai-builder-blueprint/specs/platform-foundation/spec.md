# Spec Delta

## Purpose

Defines the generic Agentic AI Builder boundary, shared platform principles, and isolated project ownership model that all other capabilities must follow.

## ADDED Requirements

### Requirement: Generic workflow platform
The system SHALL support business-process workflows across multiple domains without requiring domain-specific runtime code for each use case.

#### Scenario: New domain workflow
- **WHEN** a user submits a supported process from a domain not previously demonstrated
- **THEN** the platform SHALL plan, edit, validate, and execute it using the shared workflow model

### Requirement: Project isolation
The Agentic AI Builder SHALL be contained under `/home/raf/agentic-ai-builder` and SHALL NOT modify Praxi or the fire-detection project.

#### Scenario: Project change
- **WHEN** a contributor creates or updates Agentic AI Builder artifacts
- **THEN** the change SHALL be scoped to the Agentic AI Builder project

### Requirement: Shared contract ownership
The four named implementation owners—Suprajha, Aravind, Harihar, and Rethika—SHALL use the canonical workflow, agent, tool, API, error, permission, branching, approval, run-status, and versioning contracts as their integration boundaries.

#### Scenario: Segment integration
- **WHEN** two segments exchange workflow data
- **THEN** both SHALL use the approved shared contract rather than an independently invented format

### Requirement: Balanced pipeline ownership
The implementation SHALL assign planning, capability authorization, UI/API integration, and runtime/observability to separate owners with no owner responsible for the entire platform.

#### Scenario: Workstream assignment
- **WHEN** implementation tasks are assigned
- **THEN** Suprajha SHALL own planning, Aravind SHALL own agents and tools, Harihar SHALL own existing UI integration and workflow APIs, and Rethika SHALL own runtime and observability
