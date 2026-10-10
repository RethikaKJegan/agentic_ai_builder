# Harihar workflow API and UI boundary

This delivery preserves Mesh/Next.js App Router and wraps the existing Python planner/registry. No planner, registry, runtime or connector implementation is changed. Shared contracts are unchanged. Authentication and SQLite are explicitly local development adapters selected with the user's authorization; production login/PostgreSQL are not delivered.

## Transport

Browser routes use the `/api/backend` prefix. Next.js forwards them to the server-only `BUILDER_API_URL` (default `http://127.0.0.1:8000`). FastAPI accepts the listed paths without that prefix. Development session and proxy hosts are restricted to loopback; bind both servers to `127.0.0.1`. Development sessions are disabled unless `BUILDER_DEV_AUTH=1`. Session cookies are HttpOnly and SameSite strict; allowed browser origins are server-configured. Browser-supplied authority is rejected. Replace the local session adapter before remote deployment.

Every mutation submits `{request_id, operation, idempotency_key, payload}`. GET request IDs use a query parameter. Every response is `{request_id, status, data}` with safe failures in `data.error`; data includes correlation/contract-version metadata. Legacy planner top-level errors are normalized without modifying Suprajha's service. Raw provider exceptions, credentials and validator values are never returned. Generated Zod validators derive from the shared JSON schemas and are checked for drift.

| Method/path | Canonical operation | Payload/result |
| --- | --- | --- |
| GET `/session` | Transport-only session bootstrap | Server auth context, local mode, planning/runtime/approval availability flags; HttpOnly cookie |
| POST `/workflows/plan` | `plan_workflow` | Objective and optional context; returns `data.workflow` proposal |
| GET `/workflows` | `list_workflows` | Canonical documents in `items,total,has_more,next_cursor` |
| GET `/workflows/{id}?version={version}` | `get_workflow` | Latest or exact revision; `data.workflow` |
| PUT `/workflows/{id}/versions/{version}` | `save_workflow_version` | `workflow_id,workflow_version,base_version,workflow`; next draft revision |
| POST `/workflows/{id}/validate` | `validate_workflow` | Exact saved `workflow_id,workflow_version`; structural validation and state |
| POST `/workflows/{id}/approve` | `approve_workflow` | Exact reference plus `action: approve` or `publish`; server approval/publication permissions and prior validated/approved state required |
| GET `/tools` | `list_tools` | Existing registry discovery envelope; safe metadata, no credential IDs or executable grants |
| GET `/agents/capabilities` | `list_capabilities` | Existing registry capability collection |
| POST `/workflows/{id}/execute` | `execute_workflow` | Exact workflow reference and `inputs`; unavailable until runtime delivery |
| GET `/runs/{id}` | `get_run` | Runtime consumer boundary; unavailable until runtime delivery |
| GET `/runs/{id}/events` | `list_run_events` | Canonical run-event collection; unavailable until runtime delivery |
| POST `/approvals/{id}/decision` | `decide_approval` | Approval ID, exact workflow reference, approved/rejected decision; unavailable until trusted approval delivery |

`action`, `base_version` and success-data projections are transport implementation details within the shared envelope's object payload/data. No shared operation names or contracts were added. Runtime DTO projections must be reviewed with Rethika before connecting a live service. There is no accepted `list_runs` or `list_approvals` operation, so global run/approval collection discovery requires shared-owner agreement; current consumer views use an exact run ID and its approval references.

## Canonical mapping and storage

Canonical documents remain authoritative. Canvas IDs/kinds, references, edges/outcomes, conditions, approval gates, stakeholders, inputs/outputs, model/schema/limit data, execution/error policies and unknown metadata are retained. Positions map to optional `layout`. Visual hierarchy/collapse data lives in `configuration.ui`; role/parent/combine execution semantics fail validation until downstream review rather than being silently executed. Agent UI IDs are workflow-scoped to avoid collisions between planner agent IDs; outgoing canonical IDs are preserved.

Remote workflow/agent view models are in memory only. They are excluded from `mesh-local-drafts-v1`; saved documents are loaded from SQLite on refresh. Draft-only browser state is retained. Agent name/fallback/memory/guardrail controls without a workflow-agent contract mapping are unavailable on server-backed agents. Editable role, goal, instructions, model, temperature, token limit and output schema map into canonical agent fields. Local catalogs/settings never grant server authority.

Saving checks the current base version transactionally. Content edits produce a new draft version; validation/approval/publication update the lifecycle of that exact revision. SQLite also persists workspace/subject-scoped idempotency responses; duplicate mutations return the original result, different payloads with the same key fail, and stale saves fail with `REVISION_CONFLICT`. Provider planner idempotency remains process-local as documented upstream.

Workflow-schema-v1 does not permit `validating` or `validation_failed` in `workflow.status`, despite the lifecycle vocabulary including them. Structural failures therefore retain canonical `draft` and record `metadata.validation_state: validation_failed`. The UI displays actionable errors and does not treat failed drafts as executable.

## UI behavior and remaining dependencies

- Existing routes, Mesh styling, local canvas editing, patterns, hierarchy, undo/redo and mobile navigation remain.
- API-unavailable screens remain navigable; only functional/authorized mutations appear.
- Planner proposals are saved before navigation. Save/validate show actual returned revisions and correlation references. Unsaved edits must be saved before lifecycle actions.
- Default development builders lack approval/publication/execution permissions. Admin/approver identities require server configuration; the UI cannot assign roles.
- Approval/publication fails closed for missing trusted agent registrations, capability/tool assignments, unresolved requirements and external writes requiring the approval service. Configured, registered agents with authorized tools can pass these gates. There is no client-created authorization reference.
- Registry defaults to an empty, unconfigured workspace; no documentation fixture is installed as a real tool. Harihar's adapter loads explicit server configuration through Aravind's registration APIs and checks exact assignments through `assign`/`revalidate_assignment`. Discovery alone shows `requires_assignment`; workflow responses additionally return a safe `registry_review` projection.
- Run/approval DTO consumers handle pending/approved/rejected/timed-out/unmatched states, exact revision binding, duplicate events and impossible transitions. They are tested with injected contract fixtures. Production availability flags remain false and the corresponding server routes return unavailable errors to authorized callers.
- No connector calls, simulated planner execution, fake approval decisions, or fake run records were restored. Pure legacy simulator tests remain isolated regression tests. The test-only HTTP server explicitly injects a deterministic planner and creates an ephemeral local database.

## Rethika execution inputs and review request

Rethika must receive and review all of the following before execution is enabled:

1. An exact server-loaded canonical workflow ID/version and approved/published revision document, with validation/review provenance. Planner proposals and browser drafts are not execution grants.
2. Canonical node/edge references and declared branch outcomes, approval gate IDs/roles/rejection/timeout configuration, execution/error policies, and agent limits. Review hierarchy semantics separately; currently unsupported hierarchy configurations fail validation.
3. Exact Aravind-issued authorized assignments binding subject/workspace/workflow/agent/tool and their revisions, schemas, scopes, destinations, policy revision and opaque authorization reference. The trusted Python boundary `app.state.workflow_service.registry_adapter.execution_assignments(workflow, auth)` supplies these only after revalidation; it is not an HTTP/browser endpoint. Runtime must enforce the approved revision, authenticated subject and budgets before calling it and revalidate before each tool use. Process-local references cannot be replayed after restart or across instances.
4. Trusted server authentication and permission/scope evaluation. Development builder identity is a local POC adapter, not production login or runtime authority.
5. Execution envelope `execute_workflow` with workflow ID/version, input object, request ID and stable idempotency key. Rethika owns durable run identity, idempotent side effects, execution and budgets.
6. `get_run` success data containing `run: {run_id,workflow_id,workflow_version,status,approvals}`; event collections containing canonical `run-status-versioning-v1.run_event` items. Review this projection before wiring runtime transport.
7. Approval projections `{approval_id,workflow_id,workflow_version,status,allowed_decisions}`; the trusted runtime must provide current gate authority and matched references. Authorized `decide_approval` responses must retain the exact binding. UI controls never decide a gate locally.
8. Safe error envelopes and correlation IDs, including unavailable/denied/expired/stale/mismatched approvals and assignments.

Rethika's review is requested through repository handoff documentation only. No external notification or acceptance is claimed. Operator registry configuration, runtime/approval integration, run-list contract agreement and Rethika acceptance remain required for end-to-end execution.

## Trusted registry configuration

Set `BUILDER_REGISTRY_CONFIG` to an operator-owned JSON file inside this repository, preferably in ignored `.local/`. The empty template at `docs/contributors/examples/harihar-registry-config.json` grants nothing and is never loaded automatically. No provider secrets belong in this file. Configuration outside the repository, detected secrets, unknown fields, malformed registrations, wildcard subject grants and invented approval evidence fail startup with a safe error.

| Configuration field | Meaning |
| --- | --- |
| `policy` | Explicit `WorkspacePolicy` fields for `local-workspace`: agent permission ceilings/limits, approved providers/destinations, opaque credential references with provider/scopes, quota/risk/cost/timeout/retry limits. Credentials are references only, not proof of provider connectivity. Nonempty `approval_grants` is rejected; real evidence must come from Rethika. |
| `agents` | Complete `agent-contract-v1` definitions, including guardrails and retry policy; loaded using `register_agent`, never expanded from planner/browser authority. |
| `tools` | Entries `{definition, credential_reference?}` with complete `tool-contract-v1` definitions; loaded using `register_tool`. |
| `bindings` | Exact `{workflow_id,workflow_version,agent_id,capability,tool_id,input_schema,output_schema,destination?}` mappings, supplying trusted schema/destination context to `assign`. Each new revision needs its own mapping. |
| `subject_permissions` | Explicit connector permissions for the local admin/builder, constrained to `policy.agent_permissions`. Does not grant lifecycle/management powers. |
| `subject_scopes` | Explicit connector scopes for the local admin/builder. Viewers/approvers do not inherit these grants. |

Default builders additionally have `tools.assign` so the adapter can ask Aravind to evaluate requirements; that permission does not bypass tool/agent permission, scope, quota, risk, credential, destination or approval checks. Browser payloads cannot supply configuration or trusted identity. Embedded agent fields must match the registered definition. Editing instructions/model/limits requires an accepted configured definition and a new workflow revision; no automatic privilege expansion occurs.

Workflow read/save/validate/approval/publication responses include `registry_review: {workflow_id,workflow_version,ready,reason_codes,items}`. Items identify the agent/capability/tool, agent/tool/policy versions when available, `authorized|pending_approval|denied`, approval requirement and safe reason codes. Credential IDs, approval/authorization references, raw errors and schema/destination bindings remain server-side. The existing inspector and lifecycle controls show this projection for the matching revision only. Publication always repeats server checks; UI readiness is not authority.

Approval fills canonical `agents[*].allowed_tool_ids` from server-issued assignments. Creating a subsequent editable revision clears tool grants/configuration references in the outgoing client mapping; the server also rejects submitted executable grants. Idempotent save/approval/publication responses survive refresh/restart, while registry references remain process-local and are obtained/revalidated in the current instance. Cached authorized references are revalidated rather than silently replacing a revoked grant. Denied/pending results never become execution grants.

The loader owns registrations for its service instance. Change accepted agent definitions/bindings through operator configuration and restart/reload the complete adapter with its registry; do not mutate its agent snapshot separately. No registry-management HTTP endpoint is exposed. Runtime policy/quota/approval changes must use Aravind's trusted public service methods and keep adapter configuration consistent. Rethika still owns connector calls, quota consumption, durable execution, live gate decisions and external-write approval evidence.
