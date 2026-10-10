# Spec Delta

## Purpose

Executes only validated and authorized workflow revisions with explicit branches, approvals, budgets, connector controls, run records, and redacted observability evidence.

## ADDED Requirements

### Requirement: Revalidate before execution

The runtime SHALL revalidate the requested workflow revision, agent definitions, tool assignments, permissions, approvals, and version state immediately before starting a run.

#### Scenario: Valid approved revision

- **WHEN** an execution request references a current authorized revision with all required approvals
- **THEN** the runtime creates one run and begins execution with a correlation ID

#### Scenario: Stale or unauthorized revision

- **WHEN** a revision is stale, invalid, revoked, or unauthorized
- **THEN** the runtime rejects execution and creates no external side effect

### Requirement: Execute graph control safely

The runtime SHALL execute workflow dependencies, deterministic nodes, agent tasks, conditions, branches, retries, timeouts, and failures according to the accepted workflow and control contracts.

#### Scenario: Conditional branch

- **WHEN** a condition produces an accepted outcome
- **THEN** only the matching successor path executes and the selected outcome is recorded

#### Scenario: Unmatched condition

- **WHEN** no condition outcome matches
- **THEN** the run pauses or fails according to policy and does not silently continue

### Requirement: Enforce approvals and budgets

The runtime SHALL pause for required human approval and enforce model, token, tool, retry, duration, cost, and side-effect budgets.

#### Scenario: Approval rejection

- **WHEN** an approver rejects a pending action
- **THEN** the run records the rejection and does not invoke the blocked external action

#### Scenario: Budget exhaustion

- **WHEN** a configured execution budget is exhausted
- **THEN** the runtime stops or pauses the run with a stable error and recorded reason

### Requirement: Invoke authorized connectors

The runtime SHALL invoke only assigned tools using opaque credential references, approved destinations, timeouts, retries, and idempotency controls.

#### Scenario: SMTP success

- **WHEN** an authorized SMTP assignment has a valid credential reference and approved destination
- **THEN** the runtime sends the email and records a redacted connector result

#### Scenario: Missing authorization

- **WHEN** a connector lacks credentials, scope, assignment, or destination approval
- **THEN** the runtime rejects the action before provider invocation

### Requirement: Record safe run evidence

The runtime SHALL record unique run IDs, legal status transitions, events, correlation IDs, errors, approvals, retries, and redacted traces without secrets.

#### Scenario: Traceable completed run

- **WHEN** a run completes or fails
- **THEN** its final state, events, version, policy decisions, and trace reference are queryable

#### Scenario: Secret-bearing provider error

- **WHEN** a provider returns an error containing sensitive data
- **THEN** persisted records and traces contain only the accepted redacted error format

### Requirement: Review lifecycle and trigger contracts before implementation

The implementation SHALL use jointly reviewed versioned contracts for releases, triggers, automation identities, lifecycle operations, and overview updates. It SHALL reuse Aravind's registry authorization and Harihar's existing UI/API boundary without silently extending accepted v1 contracts or changing Harihar's specifications.

#### Scenario: Missing shared contract

- **WHEN** an activation or trigger operation lacks an accepted contract or supported adapter
- **THEN** implementation records the dependency and the UI does not claim the operation is available

### Requirement: Activate published releases reliably

The runtime SHALL activate only validated approved releases with authorized supported trigger bindings, idempotent publication, and durable recovery. Publication SHALL NOT itself execute business actions.

#### Scenario: First publish

- **WHEN** an authorized user publishes a valid approved revision and all required trigger registrations succeed
- **THEN** the release becomes active, configured matching events can create runs, and publication itself invokes no business tool

#### Scenario: Failed activation or duplicate request

- **WHEN** required trigger activation fails or the same publish request is retried
- **THEN** failure preserves the previous active release and compensates partial registrations, while retries reconcile the same operation without duplicate releases or subscriptions

### Requirement: Detect and dispatch supported events

The runtime SHALL support explicitly configured provider-event, polling, and schedule adapters with source verification, workspace isolation, event schema validation, input mapping, filtering, durable checkpoints, and deduplicated queued execution under a trusted authorized automation identity.

#### Scenario: Matching event

- **WHEN** a verified event matches an active trigger binding
- **THEN** the runtime persists a dispatch job bound to the selected release and revalidates authorization before executing its graph

#### Scenario: Duplicate or invalid event

- **WHEN** an event is duplicated, unverified, outside the configured workspace/resource, invalid, or excluded by filters
- **THEN** no additional run is dispatched and a safe disposition is recorded

#### Scenario: Restart or polling recovery

- **WHEN** the service restarts after accepting an event or detecting a change
- **THEN** durable receipts, checkpoints, jobs, and subscription reconciliation prevent lost accepted work or duplicate dispatch, and process-local registry references are reauthorized before use

#### Scenario: Self-generated event

- **WHEN** an output action produces an event excluded by the configured causation or bot filters
- **THEN** that event does not create an unbounded workflow loop

### Requirement: Display live operations in the Workflows tab

This change SHALL provide live workspace-scoped operational visibility in the top-level Workflows tab outside individual editors, using the existing UI design. It SHALL show created drafts, published revision, activation health, active run count, latest run state, and pending approvals, with authorized Run, Edit, and Delete actions.

#### Scenario: Multiple workflows operate independently

- **WHEN** a published workflow receives events while a user views the Workflows tab or creates or edits another workflow
- **THEN** live summaries update without opening each editor and unrelated editing remains available

#### Scenario: Waiting or disconnected overview

- **WHEN** a release is active with no running execution or the live connection is unavailable
- **THEN** the UI distinguishes waiting from running and displays stale connection state with snapshot reconciliation on reconnect

### Requirement: Isolate drafts and republish from the editor

The implementation SHALL preserve immutable published revisions while editing drafts and SHALL use the top editor Publish or Republish button to activate reviewed changes. Cutover SHALL be atomic, concurrency checked, and auditable.

#### Scenario: Edit an active workflow

- **WHEN** the user chooses Edit from the Workflows tab and saves changes
- **THEN** only the draft changes and incoming events continue using the active release until successful republishing

#### Scenario: Republish with existing runs

- **WHEN** a new approved draft is successfully republished
- **THEN** new dispatches use the new release while existing runs and already-bound jobs retain their original release and the overview reports the updated version

#### Scenario: Conflicting publication

- **WHEN** two editors publish against the same expected active version
- **THEN** optimistic concurrency prevents an unnoticed overwrite and the losing request receives an actionable conflict

### Requirement: Disable and delete workflows safely

The implementation SHALL support authorized disablement and confirmed idempotent deletion from the Workflows tab, preventing new dispatch and preserving retained audit evidence. Deletion SHALL revoke workflow-specific triggers, cancel queued jobs, and request cancellation of running work at safe boundaries without claiming reversal of completed external actions.

#### Scenario: Delete while events or runs are active

- **WHEN** an authorized user confirms deletion during execution or incoming event delivery
- **THEN** a durable tombstone blocks new runs and approval resumption, queued jobs are cancelled, running workers receive cancellation, and external effects already performed remain truthfully recorded

#### Scenario: Cleanup failure or publish race

- **WHEN** provider cleanup fails or publication races with deletion
- **THEN** local dispatch remains disabled, cleanup is retried with visible status, publication cannot revive the workflow, and shared credentials or other workflows' subscriptions remain unaffected

#### Scenario: Disable and re-enable

- **WHEN** a user disables a published workflow and later requests activation
- **THEN** new dispatch stops while disabled, existing-run policy is explicit, and activation revalidates authorization and subscriptions before resuming
