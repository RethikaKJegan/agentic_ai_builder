# Handoff — Harihar

## Connected existing Semantic Intelligence canvas — 2026-10-22

Deployed an in-place frontend canvas update: key-backed identifier resolution, truthful source membership for disconnected components, retained original semantic predicates/review authority, compact label-aware layout and scoped inspection. Current live view: 29 entities + 3 sources, 42 existing relationships + 5 source links, zero isolated nodes. 22 focused tests, types/lint/build/contracts/OpenSpec and isolated/live desktop/mobile checks pass. Backend graph, workflow scope/steps/approval gates and connection IDs verified unchanged; frontend alone restarted. See `docs/semantic-intelligence-canvas.md` and `openspec/changes/semantic-connected-canvas/tasks.md`.

## Fixed workspace website login — 2026-10-22

Owner-authorized source implementation adds Launch Workspace → /login → /app,
server-side scrypt verification, an expiring signed HttpOnly gate cookie,
protected workspace/API access and logout. Keeps local-builder/local-workspace,
connector/database storage and independent action approvals. Signed webhooks
and Google callbacks retain backend verification. 131 frontend tests, 62 backend
regressions, three production browser scenarios, types/lint/build/contracts and
strict scoped OpenSpec pass. Private credentials/config and deployment notes:
`docs/workspace-login.md`; evidence: `openspec/changes/workspace-login/tasks.md`.
Deployed after explicit owner authorization on 22 October 2026. Public HTTPS and live desktop/mobile Launch Workspace → login → /app, refresh and logout passed. Only the frontend restarted; backend/worker and saved connection IDs remained unchanged. No provider writes. Rollback artifact retained; see workspace-login tasks for evidence.

## New draft revision recovery — 2026-10-18

A successful supplier-audit planning job proposed version 2 for an unsaved
workflow. First save base 0/version 2 conflicted, followed by WORKFLOW_NOT_FOUND
on the concurrency recovery lookup. PlannerService now owns initial draft/version
1; frontend initial save also normalizes cached generated results after checking
that no saved revision exists. Existing revisions/concurrent-save recovery remain
intact. Recovered planned_b92b9315f54dec2b from its successful job result with a
normal authorized save as draft v1; no publish, approval or execution.

28 backend tests/4 subtests and 24 frontend integration tests pass, along with
types, lint, build, contracts and strict scoped OpenSpec. Deployed frontend/backend/
worker; workflow GET confirms v1, frontend HTTP 200 and RuntimeWorker ready. See
`openspec/changes/planned-initial-revision/tasks.md`.

## Google Marketplace discovery — 2026-10-18

Replaced Marketplace Slack/HubSpot integration entries with Google and a small
Connect Google action linking to Integrations. Removed the generic technical
provider card grid and setup copy; retained existing real Google account OAuth,
seven service-permission choices, collapsed tool checks and database summary.
No backend tool removal or authorization/credential/workflow changes.

30 focused tests, types, lint, production build and scoped strict OpenSpec pass.
Desktop/mobile production browser checks pass before and after deployment,
including navigation and permission dialog; OAuth was not started. Six unrelated
workflow/graph unit failures reproduced on unchanged HEAD. Previous production
build retained for rollback. Frontend active. See
`openspec/changes/google-marketplace-connection/tasks.md` for exact evidence.

## Original-plan Phase 3 source selection — 18 October 2026 (IST)

Questions now consumes current confirmed business mappings and shows a
server-derived selected-source preview with full paths, required field purposes,
eligible linking pairs and an inspectable highlighted graph. Successful results
carry the executed logical plan separately from the review preview. Queries-v1
gains optional selection_preview/executed_plan metadata; model query-intent and
workflow/agent/tool contracts are unchanged. Old plans/jobs remain compatible.

Implementation and acceptance steps: `docs/prompt-source-selection-phase3.md`.
Fresh evidence and limitations:
`openspec/changes/prompt-source-selection-phase3/verification.md`. Workspace-only
delivery; no deployment, live model/cloud validation, external notification or
contributor contract acceptance is inferred. Existing Google/procurement behavior
and Praxi files were not modified.

## Slack-to-Gmail publication diagnosis — 2026-10-10

Publication failures now include safe, structured setup requirements, rendered in the existing editor error panel. Unresolved requirements still prevent approval and publication; this change creates no registry grants or active automation. Regression coverage verifies the rejected revision remains validated without authorization references. Verification: 116 Python tests, 62 frontend tests, production Next.js build, TypeScript and ESLint PASS.

Local inspection found Slack Events webhook implementation, but no configured Slack signing secret, active lifecycle trigger binding, or `BUILDER_REGISTRY_CONFIG`. The configured outgoing Slack webhook only posts messages. The affected draft has no executable tools or agents and explicitly requires incoming Slack configuration, Gmail sending capability, reviewed event/condition mappings and durable deduplication. Previously verified SMTP delivery does not register a Gmail runtime tool. Incoming-event setup and trusted executable registrations remain necessary before this workflow can publish or run.

- **Segment:** Mesh/Next.js UI integration and workflow API
- **Status:** in-progress — UI/API, trusted registry integration and publication delivered; live runtime/approvals and Rethika review pending
- **Contract versions:** workflow-schema-v1, agent-contract-v1, tool-contract-v1, api-payloads-v1, error-format-v1, auth-permissions-v1, branching-approvals-v1, run-status-versioning-v1
- **Completed work:** New Mesh baseline migrated to Next.js App Router with simulated actions removed and local editing preserved. Delivered typed canonical clients, safe API errors/loading/correlation handling, planner-to-canvas integration, durable canonical workflow persistence, configured registry registration/assignment/revalidation adapters, exact assignment-state UI and authorized publication. API routes, mappings, UI states and downstream inputs are documented below. Tasks 1.1–1.3, 2.1–2.3, 3.1 and 4.1–4.3 complete (10/13). Live runtime approvals/runs and Rethika review remain open.
- **Verification evidence:** Next.js 16.4.0 production build/types PASS; ESLint PASS; 61 frontend tests PASS; 8 production browser scenarios PASS; 50 Python planner/registry/API tests PASS; shared contract validation and generated-validator drift check PASS; strict Harihar OpenSpec validation PASS with zero issues. API mappings are documented in `docs/contributors/harihar-api.md`; run commands are in `frontend/README.md`.
- **Known defects:** No failures in the verified implementation. Production authentication/PostgreSQL and live runtime/approval services remain undelivered. Operator-owned registry metadata must be configured explicitly; credential availability/quota are trusted snapshots, not live provider checks. Browser state and local catalogs confer no executable authority. Landing illustrations are labeled previews. Pure archive simulator tests remain isolated from product actions.
- **Unresolved decisions:** Local FastAPI/session/SQLite adapters are selected with user authorization. Production login/PostgreSQL, executable hierarchy mapping, runtime assignment consumption and run/approval collection contracts require downstream review.
- **Dependencies:** Suprajha’s workflow output and Aravind’s tool metadata.
- **Downstream notifications:** Rethika needs the approved workflow submission format and execution controls.
- **Next actions:** Configure operator-approved registry metadata through `BUILDER_REGISTRY_CONFIG` for actual workspace tools; connect Rethika's runtime/approval service using the documented DTO review; agree collection operations with shared-contract owners; obtain Rethika's execution-handoff review before declaring the segment ready.
- **Blockers:** Rethika's live runtime/approval services, collection-contract review and execution-handoff acceptance are missing. Aravind still needs Rethika's downstream review. Tasks 3.2, 3.3 and 4.4 remain open. Publication of external-write workflows requiring live approval evidence remains safely unavailable.

## Baseline replacement — 2026-10-10

`frontend/` is the active UI, and `incoming/mesh-nextjs-final.zip` is its source-only delivery archive. Use Node.js 22+ and `npm ci`, then `npm run dev` from `frontend/`. The landing route is `/`; the workspace is `/app`; the editor is `/app/workflows/[id]`. All previous workspace navigation surfaces remain reachable.

Local drafts use `mesh-local-drafts-v1`. The old archive's demo browser key is not loaded or deleted. Draft workflow/agent/settings models remain presentation data until a canonical backend adapter validates them. No backend HTTP routes, real connector calls or approval/execution grants were introduced.

Rethika should consume a future approved, canonical workflow revision plus exact revalidated registry assignment bindings and an authenticated execution request. This migration delivers the frontend baseline only; it does not supply those execution inputs. No external notifications or downstream acceptance claims were made.

## Aravind registry delivery — 2026-10-09

Suprajha’s planner handoff was explicitly accepted by Aravind. Registry implementation and local verification are complete: 35 tests passed; shared contracts valid; strict registry OpenSpec validation passed. Read `docs/contributors/handoffs/aravind.md` and `docs/contributors/examples/aravind-registry.json` for the complete service boundary, authorization policy, safe metadata, assignment bindings, and limitations. Your downstream review is required before Aravind task 4.4 can be completed. This file records notification, not your acceptance.

Consume canonical `list_tools` and `list_capabilities` discovery envelopes through the Python registry service; implement transport/client integration in your segment. Display pending approvals and denied candidates. Registry discovery does not issue executable grants.

## Harihar API delivery

The user authorized proceeding with a server-configured development identity. Implemented `workflow_api/` FastAPI transport and canonical SQLite revision/idempotency persistence, a same-origin Next.js API proxy, generated contract-derived Zod/TypeScript adapters, planner-to-canvas mapping, server save/load/validation and gated revision approval/publication. Planner error envelopes are normalized at Harihar's boundary; planner and registry implementation files are unchanged. No runtime or connector implementation was added.

Default development sessions are builder-only, explicitly opt-in and local. Canonical workflow sections and optional presentation fields are retained. Remote workflow/agent view models are excluded from browser storage. Missing trusted agent validation, tool/capability assignments, external-write approval service and unsupported hierarchy semantics fail closed. Runtime/approval availability flags remain false; product mutations are absent and authorized service requests receive safe unavailable errors. Reusable run/approval consumers are verified with explicit test fixtures, not live service execution.

Full routes, payloads, mappings, UI states, persistence behavior, remaining simulations and all eight downstream input groups are named in [Harihar API boundary](../harihar-api.md). Run instructions are in `frontend/README.md`. The earlier ZIP is a migration baseline; repository source includes the current API integration.

Verification: 46 Python tests PASS (35 upstream plus 11 HTTP/lifecycle tests); 57 frontend tests PASS (43 archive-domain plus 14 integration tests); production Next.js build/types PASS; ESLint PASS; shared-contract validation and generated-schema drift check PASS. Browser verification includes 6 production scenarios against an explicitly test-only planner/HTTP server: planner/canvas/agent/tool/branch/gate mapping, revision save/validation/reload, actionable graph failures, baseline local editing/undo, navigation and mobile layout. Final strict OpenSpec/browser results are recorded below after verification.

Final verification: all 6 production browser scenarios PASS; strict Harihar OpenSpec validation PASS with zero issues. All work and test/cache/database artifacts are scoped to `/home/raf/agentic-ai-builder`; no Praxi or fire-detection files were read or modified. Canonical contracts and planner/registry/runtime/connector implementation remain unchanged. Browser test servers shut down after verification. No paid provider/connector calls were made by this verification suite.

Task 2.2 is partially delivered: transactional save/version/validation and deterministic approval/publication work, but AI publication requires task 3.1's trusted agent registrations/assignments and remains unchecked. Tasks 3.1–3.3 have typed/UI consumer boundaries and fail-closed availability states, but live assignment/approval/execution delivery is not verified. Task 4.4 also needs Rethika's review. Do not archive or declare the segment ready.

Harihar accepts Aravind's discovery envelopes, safe metadata, exact authorization bindings and documented process-local limitations as the consumer boundary. This does not declare live configured assignments available or record Rethika acceptance. No external notifications were sent.

## Registry and publication integration follow-up

This section supersedes the earlier partial task 2.2/task 3.1 and missing-registry-adapter statements. Added `workflow_api/registry_adapter.py` to bootstrap explicit operator JSON through Aravind's public `register_tool`/`register_agent` methods, compare embedded agent definitions to registered records, and call `assign`/`revalidate_assignment` for exact workflow/version/subject/schema/destination bindings. No registry, planner, runtime, connector or shared-contract implementation was changed.

Workflow read/save/validate/approve/publish responses carry a safe `registry_review`; existing workflow controls and agent inspectors display authorized/pending/denied states and reasons. Opaque credential/authorization/approval references stay server-side. Approval populates canonical allowed tool IDs exclusively from current registry grants; new editable revisions clear executable grants and need fresh exact bindings. Changed instructions/model/limits require accepted server agent configuration. Default sessions remain builder-only with registry evaluation permission; server configuration supplies explicit connector scopes, never browser payloads. Unconfigured workspaces remain empty without product fixtures.

Verification: 50 Python tests PASS (35 upstream plus 15 API tests), 61 frontend tests PASS (43 domain plus 18 integration tests), production build/types and lint PASS, 8 browser scenarios PASS, canonical schema validation and generated-contract drift check PASS, strict OpenSpec PASS. Tests cover authorized publication, refresh/restart/idempotent publication retry, revision changes, missing scopes, viewer denial, unregistered/mismatched agents, tool revocation, unavailable/high-risk/pending-approval tools, and server-only assignment references. Browser fixtures are explicitly test-only, ephemeral, and make no provider/connector calls. All artifacts remain inside this repository.

Tasks 2.2 and 3.1 are now complete: 10/13 overall. Rethika may obtain exact currently authorized grants through the trusted Python `execution_assignments(workflow, auth)` boundary, must enforce approved revisions/budgets and revalidate before tool use. Live gate decisions/execution/history still need Rethika's services; task 4.4 remains pending their integration and Rethika's actual review. Do not archive or claim end-to-end execution.

## Rethika consumer acceptance — 2026-10-10

Rethika explicitly accepted Aravind's delivered registry boundary and Harihar's delivered UI/API execution boundary in the contributor session, including process-local authorization and local-development limitations, and authorized Rethika implementation. Fresh verification: 50 Python planner/registry/API tests PASS using `.venv-integrations/bin/python`; shared contracts PASS; all 16 strict OpenSpec checks PASS. Acceptance covers delivered inputs, not unfinished runtime integration, production authentication, live connectors, or new lifecycle/trigger contracts. No external notification was sent.

## Rethika core runtime delivery — 2026-10-10

Rethika accepted the delivered upstream registry/UI/API boundaries and has delivered the core runtime through existing canonical operations. Fresh verification: 94 Python tests (50 upstream, 44 runtime), 61 frontend tests, TypeScript, contract/drift checks, runtime dependencies and strict OpenSpec PASS. Runtime routes remain disabled by default and can be explicitly connected; no live model/email/trigger demonstration or final segment acceptance is claimed. See `runtime/README.md` and `docs/contributors/handoffs/rethika.md` for server adapters, approval/worker/grant boundaries and remaining publication/production limits.

Joint review requested for `openspec/changes/rethika-runtime-observability/contract-review.md` and its companion draft schema before release/trigger/automation/overview implementation. Suprajha reviews executable input/expression mappings; Aravind reviews trigger scopes and restart authorization; Harihar reviews lifecycle transport, DTOs and overview streams. All extension signoffs remain pending; existing shared contracts are unchanged. This is a repository handoff notification, not an external message or fabricated owner acceptance.

## Slack Socket Mode / Gmail implementation — 2026-10-10

The scoped `slack-gmail-socket-mode` change adds a product Socket Mode receiver, operator Gmail Registry bootstrap, real SMTP connector, release/dispatch/runtime workers, hidden app-token entry, and deterministic mapped draft setup. Existing drafts and shared contracts are preserved. Release execution now strips lifecycle-only context at canonical auth boundaries, retains exact publisher-bound grants and resumes automation approvals through fresh worker identity. Approvals/Runs use the server run collection so concurrent DM notification requests are visible.

Verification: 126 Python tests (10 new Slack/Gmail scenarios), 63 frontend tests, typecheck, lint, production build, shared contracts/generated-client drift and strict OpenSpec PASS. Gmail STARTTLS/AUTH/NOOP was verified with saved credentials; no email was submitted. Live Slack event/mail acceptance remains pending the operator's app-level token and team/DM/member IDs. Setup instructions: `docs/slack-gmail.md`. Email sends retain the existing per-action approval boundary; no automatic approval or contributor acceptance is claimed.

Focused browser checks: both approve and reject scenarios passed using `cd frontend && npm run test:e2e -- --config playwright.slack-gmail.config.ts`. These checks mock the API; the Python integration tests separately verify actual application lifecycle and SMTP connector logic with an offline transport.

The broader legacy browser suite was also attempted on isolated ports: 1/8 passed, 7 failed against builder controls/labels such as Create draft, Save revision and Registry review. These failures are recorded in `.local/slack-gmail-browser-tests.log` and are not counted as passing integration evidence. No builder redesign or unrelated selector rewrite was included.

## UI-created workflows with live providers — 2026-10-10

Use `scripts/run_live_backend.py` on 8000 and launch Next with BUILDER_API_URL=http://127.0.0.1:8000. The existing Overview Sheet URL field and objective drive live planning; Publish validates, approves the revision and activates its trigger metadata. The launcher creates no workflow. Runtime email approval remains a separate human action in Runs/Approvals. Supported descriptive node configuration now survives editor saving without an unsupported-runtime error.

63 frontend tests, typecheck, lint and production build passed; both focused approval browser scenarios passed with a mocked API. 135 Python tests and a synthetic live-model DAG run separately verify actual orchestration. Earlier broad browser failures remain recorded. Complete prompt/startup instructions: `docs/sheets-gmail.md`. No contributor acceptance is inferred.


## Data Intelligence Phase 5 — 2026-10-17

Delivered bounded federated PostgreSQL fact aggregation with PostgreSQL/MongoDB dimensions, complete pre-filter join checks, exact weighted aggregate merging, native average finalization and per-fragment UI evidence. Data-query contracts add the federated strategy and optional execution fragments; workflow/agent/tool contracts are unchanged. Existing ownership, management/read permissions, expiry, freshness, no-result-history and source review rules remain. Unsupported shapes retain bounded fallback; separate databases have no atomic shared snapshot. See `docs/cloud-federation-phase5.md` for exact support and limits.

Verification: 137 backend tests, 68 focused frontend/domain tests, four desktop/mobile browser fixture scenarios, types/lint/production build/contracts/strict OpenSpec passed. Deployed public real-model acceptance matched all eight cross-source category sales totals and weighted averages against independent SQL/category reads, with 2,155 fact rows and two strict joins. Live native average over 77 products also matched. Backend/frontend/worker active; no cloud data, credentials or review decisions changed. This records delivery evidence, not contributor acceptance or external notification.


## Data Intelligence Phase 6 — 2026-10-18

Delivered owned durable query jobs, shared-store claims, attempt/lease fencing, current-authority checks, progress, cancellation, one fresh recovery attempt and encrypted results retained for 15 minutes. Job/plan metadata lasts up to 24 hours. The Questions UI restores jobs after refresh, clears expired rows and preserves submission keys across uncertain responses. The production proxy forwards the exact query-job idempotency header. Worker supervision includes DataQueryJobs; API-only mode does not consume jobs. Existing synchronous execution remains compatible with its prior bound.

Data-query contracts add query-jobs-v1 and optional status/canonical envelope metadata; workflow/agent/tool contracts are unchanged. Default absolute job budget is 180 s from submission (configurable 45–300), also bounded by plan expiry; existing source/statement/precision/transfer budgets remain. This deployment retains its server-configured development identity, not newly implemented production IAM. See `docs/cloud-query-jobs-phase6.md` for exact behavior and limitations.

Verification: 178 backend tests, 103 focused frontend/domain/proxy tests, ten desktop/mobile browser fixture checks, types/lint/build/contracts/strict OpenSpec pass. Isolated tests cover real PostgreSQL cancellation, killed-worker recovery, PostgreSQL-store competing claims, cancellation/publication races and encrypted expiry. Live public federation matched eight independent category sales sums/weighted averages across 2,155 order details; the same job/result survived API restart/browser refresh. A second live active job cancelled without result rows. Services active. No connected cloud rows, credentials or relationship review decisions changed; job/plan/audit writes were normal authorized query metadata. This records evidence, not contributor acceptance or external notification.

## Mobile startup deployment correction — 2026-10-18

Reproduced the reported skeleton in mobile WebKit using the actual prior build's HTML: five JavaScript chunks returned 404 after build replacement. Restored 213 missing assets from available rollback builds without changing any current asset bytes, and restarted only the frontend. The identical old page then hydrated with no errors. Fresh desktop Chromium/mobile Chromium/mobile WebKit passed content, refresh, navigation and Questions with no final errors or overflow. Four asset-retention tests, contracts and strict OpenSpec passed. Future builds must retain the active build's static files before activation using `scripts/retain_frontend_assets.py`; see `docs/mobile-startup-assets.md` and frontend README. The physical phone's cache was not inspected. No app source, server bundle, contracts, credentials or business data changed; no contributor acceptance or external notification is inferred.

## Remaining-scope Phase 1: detailed knowledge graph — 2026-10-18

Delivered a versioned v2 metadata projection with database/schema containment,
reviewable shared business concepts/roles, evidence qualifications and conservative
Mongo reference suggestions. Existing v1 IDs/API/query consumers remain compatible.
Entity reviews are owned, audited, revision-checked, fingerprinted and marked
needs-review when structural evidence changes. Confirmation grants no join/tool
authority. The UI retains the original map and adds technical/business exploration,
details, focused filters and reviews. See `docs/knowledge-graph-completion-phase1.md`.

194 backend, 41 Google/procurement, 121 frontend/domain/proxy tests and 16 browser
fixture scenarios passed; types/scoped lint/build/contracts/OpenSpec passed.
Live desktop/mobile Chromium and mobile WebKit navigated/refreshed the real graph
without errors or overflow. Existing reviews/IDs were preserved; all 33 business
mappings remain suggested. Only a derived metadata rebuild was requested live;
no cloud reads/writes, model calls or user review decisions were submitted.
Deployment retains previous static assets; services active. Source-selection,
workflow CRUD integration, EDA/reset and physical iPhone acceptance remain later
work. This records delivery evidence, not contributor acceptance.

## Detailed graph build feedback correction — 2026-10-18

Fixed frozen parent build status and delayed detailed refresh. The detailed view
publishes accepted status, refreshes immediately after build requests, polls active
builds at one second and idle views at six seconds, and preserves navigation.
Backend inference, source data, permissions and canonical contracts unchanged.
Verification: 124 frontend/domain/proxy tests, 16 production browser scenarios,
types/lint/build/contracts/drift checks passed. Live desktop Chromium/mobile
Chromium/mobile WebKit builds became visible in 3.462/2.466/2.519 seconds without
reload, page errors or missing chunks. Frontend-only deployment retained old assets;
backend/worker not restarted. Physical iPhone testing remains separate. No external
notification or downstream contributor acceptance is claimed.

## Original-plan Phase 2 source navigation — 18 October 2026 (IST)

Completed the detailed graph's entity source paging and source-qualified clickable
relationship fields. All entity mappings are now inspectable from the entity in
100-item pages; same-entity refresh preserves expansion. Read-only/historical
navigation works while edits remain disabled. Existing graph backend, contracts,
IDs, reviews and query behavior are unchanged.

Fresh checks: 85 backend, 124 frontend/domain/proxy tests, 16 production Chromium
desktop/mobile browser fixture scenarios, TypeScript, scoped lint, isolated build,
contracts/drift, strict OpenSpec and whitespace passed. Workspace implementation
only; no deployment/restart or cloud/provider operations. Evidence and limits:
`openspec/changes/knowledge-graph-phase2-navigation/verification.md`. No external
notification or contributor acceptance is inferred.


## Original-plan Phase 4 controlled CRUD — 18 October 2026 (IST)

Added policy-scoped PostgreSQL/MongoDB point CRUD, actual Registry controller/tool
bindings and approval fingerprints, encrypted prepared evidence, current-authority
guards, durable no-replay claims and reviewed compensation. The Operations UI
supplies explicit review, counts, history and guarded recovery. Workflow/agent/tool
contracts remain unchanged; the additive operations-v1 schema governs console
requests and policy. Generated workflow wiring remains original-plan Phase 5.

Evidence: 215 backend regressions without skips, final 30 native CRUD tests
(overlapping the broader run), 134 frontend tests and 30 desktop/mobile browser
fixture scenarios; types/lint/build/contracts/drift/strict OpenSpec passed.
See `openspec/changes/controlled-database-crud-phase4/verification.md` and
`docs/controlled-database-crud-phase4.md`. Workspace implementation only: no deploy,
restart, live cloud writes, credential changes or policy activation. Cross-source
groups can partially commit; uncertain outcomes cannot be replayed. No contributor
acceptance or external notification is claimed.


Phase 4 activation follow-up — 18 October 2026: user authorized the running-app
release. Verified build zQFwuMLj3YJulWO9QmS8i and the Atlas-only phase4_records
policy are active; Builder API/frontend/worker restarted successfully. All 319
previous static assets remain unchanged. Four real local/public desktop/mobile
Chromium Operations/reload checks passed without errors or mutations. Existing
authentication/origin settings remain; individual production IAM is not added.
No cloud CRUD, model request or workflow execution was initiated by acceptance.
Rollback/evidence: .local/phase4-crud/activation/. See Phase 4 verification notes.


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

## Two-phase KG improvement: Phase 1 — 18 October 2026 (IST)

Added Business ontology entity canvas, source/evidence inspector, independent
predicate/direction review and per-connection automatic metadata refresh UI.
Backend reuses owned metadata, entity mappings and leased profiling/graph workers;
unchanged automatic checks preserve source/graph versions. New ontology-v1 and
refresh-v1 contracts are additive and do not change executable join authority.

Deployed build 7XQosrkQgXqVcqcxKZPSD retaining 332 older assets. Verification:
180 backend passes with three additional skips, 140 frontend passes, 36 production
browser fixtures and four real local/public desktop/mobile Chromium checks.
Both cloud sources completed automatic profiles without changing their revision 8
or graph revision 41. No cloud writes, messages or live model calls. Phase 2
retrieval remains separate. Scope/tests: docs/business-ontology-phase1.md and
openspec/changes/business-ontology-phase1/verification.md. No contributor acceptance
or external notification is inferred. Rollback: .local/ontology-phase1/activation/.

## Two-phase KG improvement: Phase 2 — 18 October 2026 (IST)

Renamed the visible Business ontology view to Knowledge graph. Added an owned
metadata inverted index, authenticated source preview, ranked reasons/coverage,
explicit ambiguity handling, bounded technical path expansion, reviewed-revision
checks before planning, task source assignments and persisted retrieval evidence.
The selected subgraph and actual configured Registry tools are visible before a
model call. Execution scope, query validators, database write policy and Google
approval boundaries remain authoritative; legacy API/review IDs are compatible.

Verified 154 saved datasets narrow to one model source and scoped execution
freshness remains valid. Native workflow/query/approval regressions and existing
data UI flows pass; exact evidence and limits are recorded in
openspec/changes/knowledge-graph-retrieval-phase2/verification.md and
docs/knowledge-graph-phase2.md. Retrieval is lexical over saved metadata, not an
embedding service or unrestricted semantic reasoning; current ingestion limits
and a four-source execution scope remain explicit.

Deployed build QCWDXZvX-tP8HfUkJBzCP with 356 retained prior assets. Existing
scheduled procurement work was gracefully drained before restart and scheduling
resumed afterward. Credentials and write-policy configuration hashes are
unchanged. No cloud writes, Google actions or model calls were initiated by
release acceptance. Rollback backup/assets: .local/kg-phase2/activation/.
Praxi untouched; no external notification or contributor acceptance is inferred.

## Essential Knowledge graph controls — 18 October 2026

Status: ready-for-handoff; owner acceptance pending. Knowledge graph tab now has
regeneration, automatic refresh, connection/search/status filters and graph
navigation only. Record exploration, review/edit panels and duplicate graph/mode
controls removed from the tab; services remain compatible. Single-connection
edges require both physical datasets in that connection. All-connections view
retains cross-database links. Agent retrieval remains unchanged and independent
of the display filter. Verification: 11 focused UI tests, 8 desktop/mobile browser
checks, typecheck/lint/build and read-only live browser checks. Frontend build
iqRTeb3DiyEQ8QX3iG2it deployed; backend/worker PIDs and configuration unchanged.
See openspec/changes/simplify-knowledge-graph/verification.md for evidence and the
corrected deployment health-check rollback. No external actions were executed.

### Read-only desktop KG inspector restored — 18 October 2026

Per owner correction, restored only the Inspect sidebar with node/edge mouse and
keyboard selection. Shows source metadata and actual semantic/structural evidence
traces; filters scope details and hide excluded selections. Editing/record modes
remain hidden; no backend or planner change. Verified 7 focused UI tests, 4 desktop
browser checks, typecheck/lint/build and live read-only desktop inspection. Build
RqUpt8VvfotOSokER1pp5 deployed, backend/worker PIDs/config unchanged. Evidence:
openspec/changes/restore-kg-inspector/verification.md. Owner acceptance pending.

### Manual relationship correction in Inspect — 18 October 2026

Restored only business relationship review (label/direction, confirm/reject/reset)
in Inspect, including ambiguous/needs-review edges. Uses existing guarded semantic
review API/current revision; stale/read-only sessions disabled and polling guarded
during save. No backend, planner or technical permission change. Verified 11 unit
tests, 4 desktop browser checks, typecheck/lint/build and live form enablement
without saving a real label. Frontend EleW6dZe9YkaYwp8yE9N- live; backend/worker
PIDs/config unchanged. Evidence: openspec/changes/restore-kg-manual-review/verification.md.
Owner acceptance pending. Record/technical-edit modes remain hidden.

### Presentation-focused EDA tab — 18 October 2026

Added desktop metadata overview with metric cards, field-type donut, dataset field
comparison, KG statuses and discovery coverage. Per-connection/combined scope,
manual refresh and automatic reload on metadata-revision/connection changes.
Uses saved metadata/KG GET APIs only; no record scans, fake statistics, backend
job or planner change. Empty and partial/unavailable states included. Verified
6 focused tests, 5 desktop browser checks, typecheck/lint/build and read-only live
metadata dashboard. Frontend cj3GVmZYbrPPxcDPi-qwG deployed; backend/worker
PIDs/config unchanged. Evidence: openspec/changes/data-intelligence-eda/verification.md.
Owner acceptance pending. Usage/scope: docs/data-intelligence-eda.md.

## Automatic KG selection on prompt submission — 18 October 2026

Status: ready-for-handoff, owner acceptance pending. Removed mandatory Overview
source preview, KG checkboxes, account picker and extra review/open click. Existing
model receives a bounded owned KG candidate pool and chooses one-to-four source IDs;
server validates/pins actual choices. Explicit preview API remains compatible.
Owned-source, join, stale evidence, write approval and scope guards preserved.
Existing unsaved browser edits are kept while opening the saved workflow directly.
No automatic external execution or arbitrary Google account substitution.

Evidence: backend 21/34 and planner 27 overlapping tests, 27 frontend tests,
3 desktop browser cases, typecheck/lint/build and strict OpenSpec. Build
0kxH3ezt3GIh5mNoVJwht live, config hashes unchanged. Real Northwind generation
without manual selection succeeded: 12 candidates → products/suppliers/categories
(3 sources, PostgreSQL + MongoDB), no unresolved requirements. Proposal only;
no workflow actions executed. Full evidence and limits:
openspec/changes/automatic-kg-planning/verification.md.


## Fresh manual Run intent — 18 October 2026

Fixed RunWorkflowDialog reusing the global payload-based execution key and permanently returning an older terminal run. Each new dialog now supplies its own key while retries/double-clicks inside that dialog preserve idempotency. Focused UI tests 3 passed; typecheck, scoped lint, contracts, strict OpenSpec and isolated production build passed. A broader UI file retains one pre-existing missing-useNavigate mock failure, with 24 passing tests. Frontend activation retains prior assets and leaves backend/worker/configuration unchanged. No workflow or external action was executed by verification. See openspec/changes/fresh-manual-run-intent/verification.md.
