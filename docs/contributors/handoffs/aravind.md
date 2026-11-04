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


## Original-plan Phase 5 database workflows — 18 October 2026 (IST)

Implemented trusted graph/source planning context, pinned workflow source scope,
actual Registry database tools, bounded query/record reads and run-linked prepared
CRUD with immediate owner approval before commit. Preparation and provenance are
atomic; console execution refuses workflow-owned operations. Stable delegation can
read/prepare; fixed graph nodes commit. Workflow details, Execution and Approvals
show planned sources, current previews and actual source/count/handoff evidence.
Configured existing Google tools compose through their existing boundaries.

Evidence: 440 backend regressions; final provenance hardening rerun 54 overlapping
native/HTTP tests; 41 focused UI tests; 34 desktop/mobile browser fixtures; build,
types, lint, contracts/drift and strict OpenSpec passed. Full frontend suite has
279 passes and seven confirmed pre-existing failures, reproduced against the saved
Phase 4 snapshot. See openspec/changes/database-workflow-integration-phase5/verification.md
and docs/database-workflow-integration-phase5.md for evidence, scope and limits.

Local implementation only: Phase 4 remains running; no deploy/restart, cloud CRUD,
Google action, credential/policy change or live model call. Owner manual workflows
are supported; automation and independent credential delegation remain denied. No
external notification or contributor acceptance is inferred.


## Reliable inventory report — 18 October 2026

Delivered a bounded fresh-prompt compiler using owned KG candidates and exact accepted/declared source links, deterministic stock/on-order ranking with honest watchlist labels, verified new-Sheet URL delivery and separate spreadsheet/email/calendar action gates. Registry validation and scoped connector execution enforce immediate approval evidence independently of legacy procurement automatic settings. An owner-scoped Google default reuses the user's previously selected account; explicit choices still override it. Existing frontend, credentials and database write policy are unchanged.

Verification: 183 backend/connector tests and 10 subtests passed; contracts, syntax and strict OpenSpec passed. Changes activated; Atlas/Supabase, public research and selected Google identity/capabilities verified. No live workflow was created or executed and no Google artifact was created. User performs the UI acceptance test. See docs/reliable-inventory-report.md and openspec/changes/reliable-inventory-report/verification.md for boundaries/evidence. This is a repository handoff, not an external notification or inferred contributor acceptance.


## Manual worker assignment recovery — 18 October 2026

Fixed fresh manual workers losing process-local tool approval evidence after API publication. Recovery requires the same currently authorized approver, exact workspace and validated published revision; current Registry scopes/policy and action approvals remain enforced. Fresh-service safety regression passed; 90 overlapping tests and 29 subtests passed. One unrelated empty-tool-list expectation fails unchanged against the original implementation. Real published revision preflight authorized all ten tools without running any workflow or external action. See openspec/changes/manual-worker-authorization/verification.md and its activation evidence. Existing terminal blocked runs require a new manual run; no draft rewrite or republish is needed.


## Shared business preparation Phase 1 — 4 November 2026

Ready for repository handoff; downstream acceptance not claimed. One shared service now prepares ontology dependencies/mappings, real/scenario evidence, task coverage, capabilities and current Registry candidates for investigations and general dynamic workflows. Server-owned pins survive persistence/retries and are checked at approved runtime load; a workflow-bound read-only connector rechecks current source authority. Existing graph contracts, planner, Registry and master-child/CrewAI runtime remain. The general path preserves unsupported/nonbusiness compatibility without inventing grounding.

310 distinct backend tests and 34 subtests passed across final runs, plus 12 actual isolated CLI operations; contracts/drift/strict scoped OpenSpec/diff checks passed. Source observations and generated scenario events remain distinct. No frontend edits, deployment, service restart, live policy/knowledge import, company writes or paid model tests. The operator-registerable business retrieval tool still needs normal Registry enablement/assignment; the agent factory, new client onboarding, memory and learning are not implemented in this phase.

Interfaces/schema, file inventory, exact commands, verification and limits: `docs/simpson-business-ontology/shared-preparation.md` and `openspec/changes/shared-business-preparation/verification.md`. This is an internal repository handoff, not an external notification.


## Dynamic capability composition Phase 2 — 4 November 2026

Ready for repository handoff; downstream acceptance not claimed. Added versioned executable capability contracts, constrained operation selection through the existing planner, deterministic task/agent configuration, semantic Registry matching, scoped immutable compositions and normal workflow drafts. Existing delegation/CrewAI/runtime now enforce prepared dependencies, isolated context, exact tool inputs and result/citation/receipt verification. Writes use normal deterministic tool nodes and existing action gates; model text cannot create capabilities, permissions or resource authority. Source coverage/pins and Phase 1 remain intact. Repeated generation preserves registered versions/grants.

343 distinct relevant backend tests and 34 subtests passed across final runs; eight actual isolated CLI checks produced/validated four specialists plus a master. Actual CrewAI bridge uses a fake model; controlled Gmail/Calendar/Sheets effects use fake transports, with zero calls before approval where required. No configured live model acceptance, real external writes, company writes, frontend edits, deployment or service restart. Prior Phase 1 dirty work preserved. Phase 3 memory/recovery/learning not begun.

Exact examples, commands, authorization results, tests, limitations and file inventory: `docs/simpson-business-ontology/dynamic-composition.md` and `openspec/changes/dynamic-capability-composition/verification.md`. Normal backend use requires actual enabled Registry/provider/connector/resource configuration; the CLI has an isolated read-only diagnostic Registry. This is an internal repository handoff, not an external notification.


## Dynamic platform memory/recovery Phase 3 — 4 November 2026

Ready for repository handoff, not downstream acceptance. Existing runtime persistence now supplies bounded scoped working views and durable specialist checkpoints. Validated owner/workspace experience, typed root-cause classification, source-revalidated dependency invalidation and guarded explicit recovery preserve original pins, usage, effects and audit. Missing input/knowledge fixes follow the existing immutable preparation/review lifecycle; uncertain writes require reconciliation. No new execution engine or automatic permission grant.

Immutable client packages feed shared preparation, the existing compiler/agent factory/Registry/delegation/CrewAI path. An isolated retail threshold fixture and Simpson both execute through the same runtime; actual CrewAI uses fake models. Outcome evaluation is persisted; no RL or automatic ontology publication. Historical Phase 2 composition validated with the current CLI.

316 distinct backend tests plus 34 subtests passed across the final suites, including 42 Phase 3 acceptance cases; follow-ups overlap. Contracts, strict scoped OpenSpec and diff checks pass. No frontend edits, deployment, service restart, real external/company writes or paid calls. Owner-scoped strategy sharing, new source adapter setup and write reconciliation boundaries are documented. See `docs/simpson-business-ontology/agent-memory-recovery.md` and `openspec/changes/agent-memory-recovery/verification.md` for files, schema, commands, evidence and limitations. This is an internal repository handoff, not an external notification.


## Interactive dynamic investigation UI — 4 November 2026

The existing overview/list/workspace now consume all three dynamic backend phases
through durable jobs and canonical workflow/agent/tool v1 contracts. New graphs
show actual task dependencies, action gates, checkpoints, source-backed reports,
optional knowledge and scoped memory/outcome/recovery. Historical links and
rename/delete remain compatible. No execution authority comes from presentation.

Configured-provider acceptance exposed and fixed launcher adapter registration/
preservation, procurement-decorator capability selection, protected delegation
inputs, server-owned usage opt-out settlement and exact citation schema gaps.
Actual OpenAI/CrewAI completed the previously authorized A-2022-12-013 read-only
comparison: four completed task checkpoints, two source reads, verified report.
This used a private application/registry copy and made no company writes.

Broad backend checks: 222 passed plus 24 subtests. Follow-ups: 97 passed plus
18 subtests and final 45 passed; overlapping suites, not additive. Frontend 464
passed; desktop/mobile browser 12 passed; types/lint/build/contracts/drift/strict
scoped OpenSpec/diff checks passed. Google identity, Gmail-profile and Calendar
reads passed for two managed accounts; this does not prove external writes.

Not deployed/restarted. Real Google write and Sheets resource acceptance remain
pending explicit test targets requested from the operator. No real Google effects,
live ontology import or automatic learning/publication. Prior dirty work preserved.
User flow, file inventory, exact commands, real acceptance and limits:
`docs/simpson-business-ontology/dynamic-investigation-ui.md` and
`openspec/changes/dynamic-investigation-ui/verification.md`.
Internal repository handoff only; no external contributor notification.


## Website deployment — 4 November 2026, 17:58 IST

Explicitly requested by the user after local acceptance. The tested frontend build
`ZPSoHUNQ7-5xdtbM_S8Q9` and current backend/worker code are live at
https://praxi.bellcorpstudio.com/app. All three systemd services are active.
Public normal login, unauthenticated API rejection, dynamic composition/runtime
capability flags, composition/package APIs, active worker heartbeat, connected-tool
controls, desktop/mobile rendering and an existing investigation passed. Zero
browser errors or missing frontend assets were observed. This rollout did not run
paid model calls or send/change Google data. The earlier isolated configured-model
acceptance remains separate evidence.

Saved workflow revisions (85,163), runtime runs (85,166), investigation plans/runs
(11/12), ontology versions/documents (8/24), and existing evidence environments
were verified byte-equivalent by table fingerprints after restart. No ontology
import, company-record update or scenario-data import was performed. Historical
records remain accessible; generate a new investigation to use the dynamic path.

Private database/build/source backups, public checks, screenshots and preservation
receipts are in `.local/dynamic-investigation-rollout-20261104/`. Initial readiness
correctly encountered authentication on OpenAPI; activation used authenticated
checks through the normal public gateway instead. No access check was bypassed.
Real Google write/resource acceptance still needs the requested test targets.


## Investigation recovery/details — deployed 4 November 2026, 18:33 IST

Build `4MoUMoCDpzd9kBBsOIA3I`: workflow question/account/resources moved to
Workflow details, aligned action toolbar, source-record count deduplication and
read-tool receipts. Read-only delegation no longer takes unnecessary writer locks;
storage contention retains a typed code and unknown failures direct inspection.
New runs receive only scoped sanitized prior-model-error hints, preserving evidence,
permissions, budgets and approvals. Original historical exception was discarded;
no definitive historical root cause beyond the reproduced locking flaw is claimed.

88 backend tests plus 18 subtests, 466 frontend tests, 12 browser checks and build/
types/lint/contracts/OpenSpec passed. Explicitly authorized actual OpenAI/CrewAI
hard-goal check completed all eight tasks in an isolated copy (six completed, two
qualified evidence gaps); four reads, no company/Google writes. Public login,
details/account controls, toolbar, diagnostics and mobile checks passed. Existing
workflow/run/ontology/composition fingerprints preserved. No live model replay.
See `docs/simpson-business-ontology/investigation-recovery-details.md` and
`openspec/changes/investigation-recovery-details/verification.md`. Private backups
and public checks: `.local/investigation-recovery-release/`.
