# Spec Delta

## Purpose

Connects the existing generic Mesh/Next.js workflow interface to the accepted backend contracts while preserving its established visual design and making simulated behavior explicit.

## ADDED Requirements

### Requirement: Use the accepted workflow contract

The UI SHALL read, edit, validate, and submit workflows using `workflow-schema-v1` and SHALL not create a parallel frontend-only workflow format.

#### Scenario: Load planner draft

- **WHEN** a valid planner response is opened in the builder
- **THEN** nodes, edges, agents, tools, conditions, approvals, and metadata render in the existing workflow experience

#### Scenario: Invalid workflow

- **WHEN** the API returns a workflow that fails contract validation
- **THEN** the UI shows actionable validation details and does not present it as publishable

### Requirement: Connect workflow lifecycle APIs

The UI SHALL use the accepted API, error, versioning, and idempotency contracts for planning, loading, saving, validation, publishing, approvals, execution, and run-history operations.

#### Scenario: Save a revision

- **WHEN** an authorized builder saves a valid workflow
- **THEN** the UI submits the accepted revision payload and displays the returned version and correlation ID

#### Scenario: API failure

- **WHEN** an API request fails
- **THEN** the UI displays the safe error code/message and field path without exposing provider or credential secrets

### Requirement: Display safe agent and tool metadata

The UI SHALL display agent configuration and authorized tool metadata without exposing raw credentials or implying permissions not present in the registry response.

#### Scenario: Authorized tool

- **WHEN** the registry returns an authorized assignment
- **THEN** the tool panel shows capability, provider, availability, risk, and approval metadata

#### Scenario: Unavailable tool

- **WHEN** a tool is unavailable or unauthorized
- **THEN** the UI marks it unavailable and prevents publishing or execution that depends on it

### Requirement: Represent approvals and run status

The UI SHALL render approval gates, branch outcomes, run states, events, version references, and idempotency outcomes according to the accepted control contracts.

#### Scenario: Approval required

- **WHEN** a workflow contains a required approval gate
- **THEN** the UI shows the pending state and prevents an unapproved execution request

#### Scenario: Run transitions

- **WHEN** a run changes state or receives an event
- **THEN** the UI updates status/history and rejects impossible transitions rather than displaying a false success

### Requirement: Preserve generic existing UI behavior

The integration SHALL preserve the supplied UI's generic routes and visual design while labeling local simulations and unconnected connectors accurately.

#### Scenario: Existing screen remains usable

- **WHEN** backend data is loading, unavailable, or not configured
- **THEN** the existing screen remains navigable and communicates its actual state without claiming an external side effect occurred

### Requirement: Next.js baseline without simulated actions

The frontend SHALL use the newly supplied Mesh UI through Next.js App Router and SHALL remove demo and nonworking controls while retaining functional local draft editing.

#### Scenario: Backend not yet integrated

- **WHEN** no backend adapter is configured
- **THEN** generation, connector setup, publishing, execution and approval actions are absent and their pages communicate the unavailable state without fabricated results

#### Scenario: Edit a local draft

- **WHEN** a user creates or edits a local draft
- **THEN** the UI preserves editing, layout, undo and browser persistence while explicitly identifying the draft as local
