# Spec Delta

## Purpose

Defines the generic visual workflow experience supplied in the new Mesh UI archive and migrated to Next.js App Router, while keeping it synchronized with the canonical backend workflow specification and avoiding a visual rebuild. Demo/nonworking backend actions are removed until real adapters exist.

## ADDED Requirements

### Requirement: Workflow visualization
The existing UI SHALL render agents, actions, conditions, approvals, inputs, outputs, dependencies, and connections with distinguishable visual types.

#### Scenario: Generated workflow review
- **WHEN** a valid workflow is returned by the backend
- **THEN** the UI SHALL display its nodes and edges in an editable graph

### Requirement: Workflow editing
The existing UI SHALL allow users to add, remove, reconnect, configure, and reposition workflow nodes and edit agent instructions, tools, conditions, and approval settings.

#### Scenario: Edit and save
- **WHEN** a user changes a node or connection and saves
- **THEN** the UI SHALL submit the updated canonical workflow revision to the backend

### Requirement: Visual position independence
Changing a node’s visual position SHALL NOT alter execution order or dependency semantics.

#### Scenario: Drag without reconnecting
- **WHEN** a user drags a node to a new position
- **THEN** only layout metadata SHALL change

### Requirement: Review before execution
The UI SHALL expose validation results and SHALL require workflow review and approval before execution controls become available.

#### Scenario: Invalid workflow
- **WHEN** backend validation returns errors
- **THEN** the UI SHALL show actionable errors and SHALL prevent execution

### Requirement: Backend integration without visual rebuild
The existing UI SHALL replace simulated local workflow, connector, and run behavior progressively with backend API behavior while preserving its established visual design and generic navigation.

#### Scenario: Backend-backed workflow
- **WHEN** the planner returns a workflow from the backend
- **THEN** the UI SHALL load and edit that workflow through the agreed API/client boundary instead of creating a second frontend-only workflow format

#### Scenario: Unconnected feature
- **WHEN** a connector or runtime feature is not yet available from the backend
- **THEN** the UI SHALL show unavailable or needs-configuration state and omit demo/nonworking backend actions rather than presenting a completed real integration
