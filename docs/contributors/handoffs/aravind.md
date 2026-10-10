# Handoff — Aravind

- **Segment:** Agent and Tool Registry
- **Status:** in-progress — implementation and local verification complete; downstream acceptance pending
- **Contract versions:** workflow-schema-v1, agent-contract-v1, tool-contract-v1, api-payloads-v1, error-format-v1, auth-permissions-v1, branching-approvals-v1, run-status-versioning-v1
- **Completed work:** Canonical agent validation; planner adapter; capability catalog; workspace ownership and agent revisions; approved tool registration; opaque credential-reference storage; secret rejection; capability/schema matching; subject, workspace, role, permission, scope, destination, risk, quota, budget, and approval checks; versioned authorization references; safe discovery and decision records.
- **Verification evidence:** `python3 -m unittest discover -s tests -v` — 35 tests passed (14 planner, 21 registry); `python3 scripts/validate_contracts.py` — schemas and fixtures valid; `openspec validate aravind-agent-tool-registry --type change --strict --json` — valid with zero issues. Positive and negative assignment scenarios and downstream consumer envelopes are covered by `tests/test_registry.py`.
- **Known defects:** No known failing scenarios in the verified registry scope. Persistence and transport adapters are not provided by this service layer; see limitations below.
- **Unresolved decisions:** None for the accepted registry contract boundary.
- **Dependencies:** Suprajha's planner handoff accepted explicitly by Aravind on 2026-10-09; trusted server authentication, workspace policy, credential configuration, quota snapshots, and upstream approval evidence.
- **Downstream notifications:** Harihar and Rethika receive the service boundaries and examples below through their contributor handoff files. Their acceptance is not yet recorded.
- **Next actions:** Harihar and Rethika review the consumer examples, authorization boundary, and limitations; record their review results before task 4.4 and segment readiness can be completed.
- **Blockers:** Task 4.4 requires both downstream reviews. This does not block local registry implementation, which is complete.

## Upstream acceptance — 2026-10-09

Aravind explicitly accepted Suprajha's planner handoff in the contributor session. Local review reran 14 planner tests and contract validation successfully; strict planner OpenSpec validation returned valid with zero issues. Accepted inputs are `workflow.agents[*].capabilities`, `workflow.tools[*].capability`, and `metadata.unresolved_requirements`. Planner drafts remain non-executable and contain no credential, permission, or tool grants.

The planner currently requests only `workflow.read_input` and sets its planning agent's tool-call budget to zero. The adapter preserves these values. Executable connector agents require explicit authorized definitions with connector permissions and budgets; the registry never expands planner authority automatically.

## Files delivered

- `registry/contracts.py`: canonical schema loading, safe validation failures and error envelopes.
- `registry/safety.py`: recursive rejection of raw secret fields, secret-like strings, bearer tokens, private keys, and URL credentials.
- `registry/agents.py`: agent validation and planner reference normalization.
- `registry/policy.py`: trusted workspace policy and authorization checks.
- `registry/matching.py`: conservative schema-containment checks.
- `registry/service.py`: registration, discovery, assignment, revalidation, policy updates, approval-reference ingestion, and decision records.
- `tests/test_registry.py`, `tests/fixtures/registry/`: registry scenarios and GitHub, Slack, weather, HTTP, and webhook metadata fixtures, alongside canonical SMTP and Google fixtures.
- `docs/contributors/examples/aravind-registry.json`: verified discovery, authorized assignment, and denied assignment examples.

No planner, UI, runtime, or shared contract implementation files were changed.

## Registry endpoints and service boundaries

`RegistryService.handle(request, auth)` accepts the canonical request envelope for `list_tools` and `list_capabilities`. Authentication is a separate trusted argument; payload fields cannot override it. Success and failure responses both conform to `api-payloads-v1`; errors are in `data.error`, which conforms to `error-format-v1`. Every response contains `data.contract_versions` and `data.correlation_id`. Discovery returns `items`, `total`, `has_more`, and `next_cursor`; all workspace results are returned in one collection.

Harihar owns the HTTP/client adapter. No HTTP routes or new shared operation names were invented here. The following Python service boundaries are ready for that adapter:

| Boundary | Required permission and role | Result |
| --- | --- | --- |
| `register_agent(definition, auth)` | `tools.manage`, admin | Validated, versioned agent record |
| `register_tool(definition, auth, credential_reference)` | `tools.manage`, admin | Versioned tool metadata and opaque credential binding |
| `consume_planner(response, auth)` | `tools.assign`, admin/builder | Requirements and unresolved operations without executable assignments |
| `list_tools(auth)` / `list_capabilities(auth)` | `tools.read`, authenticated allowed role | Safe workspace-scoped collections |
| `assign(agent_id, capability, input_schema, output_schema, auth, workflow_id, workflow_version, ...)` | `tools.assign`, admin/builder | Authorized assignment or pending approval; candidate exclusion reasons on denial |
| `revalidate_assignment(reference, agent_id, tool_id, workflow_id, workflow_version, auth)` | `tools.assign`, admin/builder | Current authorization decision for the exact binding |
| `update_policy(policy, auth)` | `tools.manage`, admin | Advancing policy revision; previous grants become stale |
| `update_approval_evidence(grants, auth)` | `tools.manage`, admin, trusted approval-service adapter | Existing upstream approval references; does not decide workflow approvals |
| `decision_records(auth)` | `tools.manage`, admin | Accepted, pending, and denied decision evidence |

## Capability identifiers

Accepted planner identifiers: `classify_text`, `retrieve_records`, `generate_report`, `read_spreadsheet`, `send_email`, and `send_notification`. Approved registry entries may explicitly add capabilities through admin registration. A known capability without an eligible tool remains unresolved; unknown planner tool IDs do not create registry entries or assignments.

## Assignment examples and downstream use

Read `docs/contributors/examples/aravind-registry.json`:

- **Harihar:** `harihar_discovery.data.items` contains safe metadata, versions, availability, and credential-configuration flags. Discovery never grants executable tools and does not expose credential IDs. Show `pending_approval` and exclusion reasons when reviewing assignments.
- **Rethika:** `rethika_assignment.data.assignment` binds subject, workspace, workflow ID/version, agent ID/version, tool ID/version, policy version, credential reference, destination, schemas, and required scopes. Only `authorization_state: authorized` includes `authorization_reference` and a nonempty `assigned_tool_ids` list. Revalidate the reference against current trusted authentication and policy before use.
- **Denied example:** `denied_assignment.data.error` identifies a missing-scope exclusion and provides stable codes without an executable grant or raw provider data.

Sample authorization references belong to the fixture service instance. They are documentation data and cannot be replayed in another registry instance.

## Policy decisions and limitations

- Construct authentication and `WorkspacePolicy` from trusted server sources. Never accept roles, scopes, credential references, quotas, approver identities, or policy objects directly from planner/client payloads.
- Agent definitions must remain within workspace permissions and limits; wildcards and caller-created tool grants are rejected. Every configured guardrail is required.
- Credential IDs use `cred_...` and must match workspace/provider/scopes. The registry stores no secret values and performs no secret retrieval.
- Both subject and agent permissions, subject scopes, configured credential scopes, provider approval, availability, remaining quota, risk, cost, retries, and timeouts are checked before assignment.
- HTTP/webhook destinations must exactly match both tool and workspace allowlists. Symbolic destinations such as `verified_recipients` require protected downstream resolution; the registry does not validate an actual SMTP recipient list or perform network calls.
- Schema matching proves input containment and output satisfaction conservatively. Equal self-contained schemas and simple open-object containment are supported. Unproven combinations fail closed; schema references are rejected without network resolution.
- Approval requirements yield `pending_approval` with no authorization reference or assigned tools until an unexpired trusted approval reference matches the complete assignment fingerprint and an authorized approver role and scopes. Upstream workflow approval decisions remain outside this registry.
- Revalidation rejects changed agent/tool/policy revisions, revoked scopes or credentials, and expired/revoked approvals. Runtime must separately enforce approved workflow revisions and execution budgets.
- Registry records, assignments, and audit history are process-local. Restarting invalidates authorization references. Credential availability and remaining quota are trusted configuration snapshots; this service does not contact providers, reserve quota, consume runtime budgets, or provide durable persistence. Consumers must refresh policy and revalidate before execution.

## Acceptance review

Local pass/fail evidence: full tests PASS (35/35); shared contracts PASS; strict OpenSpec validation PASS; positive/negative assignments PASS; consumer examples PASS. Harihar review: pending. Rethika review: pending. Keep task 4.4 unchecked and the segment in progress until both reviews are recorded. No external notifications were sent.

## Harihar consumer review

Harihar reviewed and accepts the delivered discovery envelopes, safe metadata, exact assignment bindings and process-local authorization limitations. The consumer wraps existing `RegistryService.handle` for discovery using a separate server-authenticated context; discovery never becomes an executable grant. Local verification reran the 35 upstream tests successfully within the expanded 46-test API suite; shared contracts and generated UI validators match. Workflow publication fails closed until trusted registry agent-validation and assignment integration is configured. This acceptance covers the delivered service boundary, not live registrations/credentials or Rethika's runtime. Rethika review remains pending; Aravind task 4.4 remains open. This section supersedes the earlier pending Harihar-review entry only.

### Harihar integration follow-up

Harihar's configuration/transport adapter now consumes existing public tool/agent registration, assignment and revalidation methods. Exact workflow/subject/revision bindings are verified; secret-free state projections reach the UI, and authorized assignments gate publication. No registry implementation or shared contract was changed. Verification passes 50 Python tests, 61 frontend tests and 8 browser scenarios, including denial/pending/revocation cases. Configuration is explicit and operator-owned; fixture credentials/tool metadata are used only by tests. Operator scope/credential/quota configuration is still needed for actual workspace tools. Rethika review remains pending and Aravind task 4.4 stays open.

## Rethika consumer acceptance — 2026-10-10

Rethika explicitly accepted Aravind's delivered registry boundary and Harihar's delivered UI/API execution boundary in the contributor session, including process-local authorization and local-development limitations, and authorized Rethika implementation. Fresh verification: 50 Python planner/registry/API tests PASS using `.venv-integrations/bin/python`; shared contracts PASS; all 16 strict OpenSpec checks PASS. Acceptance covers delivered inputs, not unfinished runtime integration, production authentication, live connectors, or new lifecycle/trigger contracts. No external notification was sent.

## Rethika core runtime delivery — 2026-10-10

Rethika accepted the delivered upstream registry/UI/API boundaries and has delivered the core runtime through existing canonical operations. Fresh verification: 94 Python tests (50 upstream, 44 runtime), 61 frontend tests, TypeScript, contract/drift checks, runtime dependencies and strict OpenSpec PASS. Runtime routes remain disabled by default and can be explicitly connected; no live model/email/trigger demonstration or final segment acceptance is claimed. See `runtime/README.md` and `docs/contributors/handoffs/rethika.md` for server adapters, approval/worker/grant boundaries and remaining publication/production limits.

Joint review requested for `openspec/changes/rethika-runtime-observability/contract-review.md` and its companion draft schema before release/trigger/automation/overview implementation. Suprajha reviews executable input/expression mappings; Aravind reviews trigger scopes and restart authorization; Harihar reviews lifecycle transport, DTOs and overview streams. All extension signoffs remain pending; existing shared contracts are unchanged. This is a repository handoff notification, not an external message or fabricated owner acceptance.
