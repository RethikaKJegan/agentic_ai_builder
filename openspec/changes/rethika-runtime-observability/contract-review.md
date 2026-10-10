# Published workflow operations contract review

Status: ACCEPTED on 2026-10-10. This review and the versioned shared schema are executable authority.
Owners: Suprajha, Aravind, Harihar, Rethika. All four owners unanimously accepted this boundary.

## Concrete proposed boundary

The accepted `shared/contracts/workflow-operations-v2.json` defines versioned
records for releases, triggers, automation identities, durable dispatch, overview
snapshots, and streams. It is additive and leaves every accepted v1 contract unchanged.

Keep accepted v1 revision/run states and API operation names unchanged. The
separately versioned lifecycle operations are activate_release, disable_release,
delete_workflow, get_lifecycle_operation, list_workflow_overview,
subscribe_workflow_overview, and ingest_trigger_event. Manual Run continues to use
execute_workflow.

| Operation | Method and path | Permission |
| --- | --- | --- |
| activate_release | `POST /workflows/{workflow_id}/releases` | workflow.publish |
| disable_release | `POST /workflows/{workflow_id}/disable` | workflow.publish |
| delete_workflow | `DELETE /workflows/{workflow_id}` | workflow.delete |
| get_lifecycle_operation | `GET /lifecycle-operations/{operation_id}` | workflow.view |
| list_workflow_overview | `GET /workflow-overview` | workflow.view |
| subscribe_workflow_overview | `GET /workflow-overview/events?after_sequence=N` | workflow.view |
| ingest_trigger_event | `POST /trigger-bindings/{binding_id}/events` | events.ingest or verified provider signature |

## Review decisions and mappings

| Area | Proposed behavior | Required review |
| --- | --- | --- |
| Release | Immutable workflow ID/version, agent/tool revisions and trigger config; preparing/active/failed/disabled/deleting state distinct from revision/run states | All owners |
| Publication | workflow.publish permission; expected release ID; idempotent operation; atomic active-pointer cutover only after all registrations succeed | Harihar, Rethika |
| Trigger permissions | Separate reviewed trigger.manage and events.ingest authority; sender/read tool scopes never imply subscription authority | Aravind, Rethika |
| Automation identity | Trusted server identity, workspace, explicitly approved scopes; fresh identity lookup before execution; never from inbound events | Aravind, Rethika |
| Registry restart | Trusted operator reconstruction followed by new exact assignments, including current approval evidence; never replay old references | Aravind, Rethika |
| Event pipeline | Verified source, protected workspace routing, schema/filter/mapping checks; receipt/checkpoint transaction; deduplicated release-bound jobs | All owners |
| Initial polling | Baseline current state at activation; no historical backfill unless explicitly authorized; checkpoint stored atomically with receipt | Suprajha, Rethika |
| Dispatch | Lease, bounded retries, dead-letter/replay policy; effect reconciliation; causation/self/bot filters; queued job retains selected release | Aravind, Rethika |
| Overview | Workspace snapshot, drafts and active versions, health, running count, latest run and pending approvals; pagination and sequence/resume | Harihar, Rethika |
| Live updates | Authenticated SSE, resume cursor, snapshot reconciliation and polling fallback; stale indicators and workspace isolation | Harihar, Rethika |
| Delete | Reviewed workflow.delete permission; confirmed idempotent tombstone; no new dispatch/resume; queue cancel; safe worker cancellation; cleanup retries | All owners |
| Audit retention | Retain minimum lifecycle/run evidence; retention duration remains an operator/shared-owner decision | All owners |

Do not conflate existing revision publication with release activation. Existing
`approve_workflow` can mark a revision published; it currently creates no durable
release or incoming subscription. Publish/Republish must not execute business actions.

## Provider inventory

- Manual execution: implemented via existing execute_workflow and bounded runtime.
- SMTP outbound send: adapter implemented; explicit reference resolver, current
  assignment, upstream approval evidence, run approval, allowlisted host/recipient
  and controlled destination are required. SMTP is not an incoming mail source.
- Provider push subscriptions: no implemented source adapter; unavailable.
- Polling sources: no implemented source adapter; unavailable.
- Schedule sources: no implemented source adapter; unavailable.
- GitHub/Google/public API smoke checks and the earlier local webhook receiver:
  not runtime trigger adapters, not restart/replay-safe event subscriptions.

A fake push/poll/schedule suite and one explicitly authorized real incoming event
source remain acceptance work after the review. No universal trigger support is claimed.

## Signoff

| Owner | Result | Evidence |
| --- | --- | --- |
| Suprajha | accepted | Workflow/input mappings, polling baseline, and workspace routing accepted unanimously on 2026-10-10 |
| Aravind | accepted | Trigger scopes, automation identity, and trusted restart reconstruction accepted unanimously on 2026-10-10 |
| Harihar | accepted | Additive v2 transport, overview/resume semantics, and UI mapping accepted unanimously on 2026-10-10 |
| Rethika | accepted | Runtime, durable dispatch, lifecycle, deletion, and acceptance boundary accepted unanimously on 2026-10-10 |

The implementation and acceptance evidence for tasks 5.3 and 6–8 remain required.
