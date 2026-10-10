# Spec Delta

## Purpose

Defines authenticated subjects, roles, permissions, scopes, and authorization decisions for workflow design, tool access, approvals, execution, and observability.

## ADDED Requirements

### Requirement: Authenticated subject context
Protected operations SHALL receive an authenticated subject with identity, workspace, role, and relevant scopes.

#### Scenario: Missing subject
- **WHEN** an unauthenticated request attempts a protected operation
- **THEN** the operation SHALL be denied with a safe authentication error

### Requirement: Role-based permissions
The system SHALL evaluate permissions for viewing, editing, validating, publishing, approving, executing, managing tools, managing policies, and viewing traces.

#### Scenario: Viewer edit attempt
- **WHEN** a viewer attempts to edit a workflow
- **THEN** authorization SHALL deny the operation without changing the workflow

### Requirement: Least-privilege tool scope
Tool execution SHALL require both workflow assignment and subject/runtime authorization for the requested capability and connector scope.

#### Scenario: Builder executes unapproved tool
- **WHEN** a builder requests a tool not assigned to the approved workflow
- **THEN** the request SHALL be denied even if the builder can edit workflows

### Requirement: Approval authority
Approval decisions SHALL require an authorized subject whose role and scope match the approval gate.

#### Scenario: Unauthorized approval
- **WHEN** a subject without the required approval role attempts to approve
- **THEN** the approval SHALL remain pending and the denial SHALL be recorded
