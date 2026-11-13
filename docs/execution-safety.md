# Shared execution safety

The existing Governance, Runs, Workflows, Approvals and Integrations interfaces use shared backend controls for Subway and Simpsons. No tenant-specific safety engine or additional navigation menu is introduced.

## Controls and enforcement

| Control | Enforcement |
| --- | --- |
| Stop run | Authenticated owner or workspace administrator; durable cancellation, expired execution lease, pending approvals closed, and no automatic recovery of cancelled work. Existing composition cancellation uses the same boundary. |
| Duration | Original run creation time survives retries and recovery. Workflow, agent, request, tool, delegation and step bounds intersect; workers also expire queued/approval-waiting runs. Existing status contracts use `blocked`/`failed` plus typed timeout reasons. |
| Access | Current Registry bindings, tenant identity and source generations remain authoritative. Workspace restrictions are checked at dispatch, source ownership, query validation, discovery and query-worker checkpoints. Read-only mode blocks registered external writes and direct database execution. |
| Approval | Exact proposed action, schema validation, payload digest, authorised gate roles, expiry and current permissions. A workspace policy can add a durable approval for a fixed tool action. Delegated writes still require a reviewed workflow gate; missing authority blocks execution. |
| Limits | Persisted workflow/agent usage, additional workspace caps and original run policy intersect. A later workspace restriction takes effect before subsequent work; relaxing workspace settings cannot loosen a run's original snapshot. Explicit retry caps also bound model corrections and evaluator retries. |
| Duplicate actions | Existing run, event, scheduler and connector journals are retained. A shared action journal additionally keys an external effect by run, reviewed workflow, tool and resolved payload. Completed receipts are reused; submitted actions without a confirmed receipt require reconciliation. |
| Recovery | Existing checkpoints, original source/ontology pins and verified receipts are retained. Recovery does not reset deadlines or usage, resurrect cancellation, or replay uncertain external writes. |
| Evidence | Durable events carry run/workflow/correlation, workspace and actor references. Approval actors retain the reviewer identity. Policy updates have append-only revision/hash audit records. Runs expose stop reasons, reserved/settled usage and uncertain effects. |

## Existing Governance menus

Execution safety contains read-only and approval switches, an expandable limits section, restricted resource identifiers and a single Save changes action. Saving requires a trusted administrative role, `workflow.edit`, `workspace:write`, and the current policy revision. Concurrent edits return a conflict.

Usage & Limits displays reported values. It never substitutes example usage or invented organisation spending caps. Delegation structure comes from the reviewed workflow; concurrent capacity comes from trusted runtime configuration. Missing measurements are explicitly marked.

Communication preferences remain labelled browser preferences. They do not disable backend security checks. Tenant isolation, schema validation, exact Registry authority and audit recording have no off switch.

## Persistence and compatibility

Additive tables: `runtime_governance`, `runtime_governance_audit`, `runtime_action_effects`, `runtime_operation_controls`, and `data_query_governance`. Existing application tables, credentials, ontology versions, data manifests, schedules, receipts and workflow definitions are retained. Existing per-workflow write/approval restrictions remain effective when no extra workspace restriction is configured.

Manual planning and existing domain jobs use the same policy context. Read-only status polling does not create empty accounting records. Durable query submissions bind their owning run atomically; query monitors stop cancelled parents and use existing PostgreSQL cancellation where available. Source restrictions also apply when reading cached query results.

## Practical limits

Cancellation fences further work and discards late model results. Python cannot safely kill an arbitrary synchronous SDK call. In-flight calls can continue until their transport deadline; adapters may implement `cancel_invocation` where supported. An action accepted by an external provider cannot generally be recalled. Valid late receipts are recorded without resuming the stopped workflow; otherwise its outcome remains unknown.

SMTP Message-ID is not an exactly-once delivery guarantee. Unknown submissions are not automatically retried. Model input screening is best effort; schemas, scoped credentials, reviewed tools and backend authorization enforce the execution boundary.

Provider costs remain explicitly estimated rather than settled charges. Call and token ceilings are available; existing reviewed cost reservations remain in place where configured. This release does not invent provider pricing or an organisation billing ledger.

Policies use the actual existing workspace, reviewed workflow/agent and run scopes. Corporate department inheritance and individual employee directory provisioning are not introduced by these controls.

## Verification and deployment evidence

The complete command logs, exact candidate manifests, preservation inventories, consistent database backups, browser evidence and deployment report are retained privately in `.local/execution-controls-release-20261113/`. Tests using controlled external transports are distinguished from authenticated production smoke tests. Optional PostgreSQL tests require their configured test server; production deployment here uses the existing SQLite application stores.
