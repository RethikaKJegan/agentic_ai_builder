# Handoff — Harihar

## Generic Subway assessment query compatibility — deployed 12 November 2026

Assessment selection now fully validates requested base fields, then uses canonical native IDs without changing filters, ordering or page bounds. Handles extra/missing/empty detail projections across all eight assessments. Binding/invocation API failures retain typed runtime codes and explicit recovery categories. The exact failed ten-field query now reconciles eight orders identically to an ID-only baseline in an isolated real-data replay. 74 candidate acceptance and 96 integration/isolation tests passed; focused 23-test coverage overlaps. Subway-only restart; frontend, Simpson, canonical sources, credentials, schedules and history preserved. No live workflow/model/external action was retried. See `openspec/changes/subway-assessment-query-contract/verification.md`.

## Subway actual delivery cleanup — deployed 12 November 2026

Removed backend-forced demonstration prefixes and normalized actual report/email/Calendar/Sheet content before exact approval. Legacy prepared content is cleaned at new delivery input resolution; recipient/resource/date authority, citations, figures and canonical provenance remain unchanged. 75 final affected tests passed; 119 wider regressions passed on the isolated candidate before the defensive legacy-context fix. Actual saved report replay verified plaintext/HTML MIME, Calendar JSON and Sheet payloads offline. Only Subway backend restarted; frontend/Simpson and protected data unchanged. One configured-provider assessment rehearsal failed before reporting, and automatic approval review rejected an additional external-model rehearsal; neither is claimed as passing evidence. See `openspec/changes/subway-clean-delivery-content/verification.md`. This supersedes the earlier backend Demo data insertion, while retaining stored provenance.

## Subway clean workflow UI — deployed 12 November 2026

Frontend-only build `6csstwFbPIsnB_HGLFB-X` removes repeated demonstration wording/badges, supplier prefixes and boilerplate from Subway workflow tabs, node inspectors, Knowledge Map and rendered diagnostics. Meaningful evidence/currency notes remain; canonical records/IDs/provenance and outgoing payload generation are unchanged. 116 frontend tests, eight browser journeys, types/lint/build and hosted desktop/mobile checks passed. Only frontend restarted; all backend PIDs and Python hashes, including Simpson and Subway, remain unchanged. See `openspec/changes/subway-clean-workflow-ui/verification.md`. This supersedes the visible Demo data indicator in the prior presentation entry.

## Subway compact presentation and Knowledge Map — deployed 12 November 2026

Fixed the authenticated Knowledge Map list parser rejecting the demo ontology at revision zero; exact authorized demo pins load independently of optional module labels. Subway display copies and new prepared report/email/Calendar/spreadsheet content use Demo data; canonical provenance and exact payload authority remain unchanged. Deployed isolated Subway backend and frontend build `rdAkVLyxq_5vug08JkGqd`. Final affected backend 26, wider regression 119, frontend 80 and desktop/mobile browser six checks passed (overlapping suites). Hosted old-report/map/diagnostics checks and a fresh ordinary provider-backed run passed; an earlier evaluator-blocked attempt is retained and reported separately. No external delivery or Simpson account/data/workflow mutation. See `openspec/changes/subway-compact-presentation/verification.md`.

## Provider-managed investigation tokens — 3 November 2026

Explicitly user-approved backend/worker deployment removes investigation application input/output-token and cost ceilings; provider request omits max_output_tokens for planning and analysis. Effective policy exposed in capabilities/reports. Calls/time, strict citations and source scopes remain. Truncated optional final narrative retains a qualified source report; original failed run stays preserved. 130 tests plus 28 subtests, followed by 7 focused checks passed (overlap); actual saved-evidence local-provider replay and live authenticated policy checks passed. No paid replay/company writes or frontend/knowledge changes. Existing workflows can start new runs. See `openspec/changes/investigation-provider-token-policy/verification.md`.

## Investigation list rename/delete — 3 November 2026

Deployed build `A8GKRkwv5mpFqeJJ5XTSx`: three-dot menu beside each business investigation, persistent display-name editing and confirmed deletion with retained audit history. Owner-scoped metadata preserves immutable plans; current workflow.edit/delete and workspace write permissions enforced. Active work blocks deletion. 46 backend, 6 frontend presentation and 6 desktop/mobile browser checks passed; types/lint/build/contracts/OpenSpec passed. Actual public menus/dialogs checked without changing user workflows. No paid calls or company writes. Details: `openspec/changes/investigation-list-actions/verification.md`.

## Report schema fix and evidence rollout — 3 November 2026

After explicit user deployment approval, backend/worker restarted and evidence package imported as live revision 8. Strict request-specific report schema transport prevents unconstrained JSON generation; local validation and one-call budgets remain. Explicit negative goals no longer request excluded warranty tasks. 82 affected tests plus 10 subtests and 2 diagnostic checks passed; authenticated public session/worker/registry checks passed. Original versions/runs preserved byte-identical, no company writes or paid deployment calls. Existing plans need regeneration; failed runs remain inspectable. See `openspec/changes/investigation-report-schema/verification.md`. This supersedes the local-only rollout status below.

## Task-specific evidence refinement — 3 November 2026, local only

Backend mappings/code/date resolution, conservative candidate reads, requirement registry, normalized gaps/recovery and isolated scenarios are implemented. Broad regression: 689 passed; final affected packet/scenario/report suite: 80 passed (overlapping coverage). Twelve independent read-only source checks and real history CLI passed. No frontend, live import, deployment, company writes or paid calls. Existing shared contracts are unchanged; future rollout needs fresh versioned knowledge/plans. See `docs/simpson-business-ontology/evidence-refinement.md` and `openspec/changes/task-evidence-refinement/verification.md`. This is an in-repository handoff, not external notification.

## Warranty knowledge and stable revisions — deployed 2026-11-01

Live build `2ffYX6_wB2IeyuqzFrhrw` fixes the empty knowledge experience and async revision selector reset. Imports four reviewed source-cited implementation-derived warranty drafts atomically/idempotently from the existing owned code. Shows invoice/sale/hour limits, basis, selector/source hash and original quotations; unknown effectivity, account/model scope and exclusions stay unknown. Code is not relabelled written policy. Stable ID/loading/stale handling and explicit refresh propagation connect newly saved/imported drafts to case comparisons.

92 backend, 239 scoped frontend plus one additional refresh case (ten-test policy file passed), eight desktop/mobile browsers, types/lint/build/contracts/OpenSpec passed. Actual live import added exactly four policy heads/revisions/audit events; source/ontology/job/graph data and original416 records/three versions unchanged. Live desktop/mobile source/draft/export/selector/case-comparison/assessment checks passed. No paid model/company-source call or provider write. Fresh backup/rollback/evidence private under `.local/business-ontology/warranty-knowledge-20261101/`. See policy-drafts.md and latest verification. Authoritative missing company evidence and deferred individual login remain distinct from this implemented functionality.

## Generation source-classification reliability — deployed 2026-11-01

The two newly reported engine failures both involved unsupported policy/code rule labels. Fixed generation itself: provider enum choices now depend on supplied source kinds; a generation-only preparation step downgrades unsupported authority labels to proposed logic using the rule's actual citations. Strict citation/reference/compiler validation is unchanged. Job/version adjustment provenance and UI explanations preserve original/final classifications. One first-attempt provider call suffices in the reproduced failure-condition tests; no additional paid call or live job retry was made.

Live build `gWzXNxEi87sxiMImvcTFs`; 41 generation +103 related backend checks, 237 relevant frontend tests, six staged desktop/mobile checks, types/lint/build/contracts/OpenSpec passed. Initial fixture failure and successful rerun are documented. Actual source choices verified for all twelve modules; no policy source is currently supplied. Live desktop/mobile navigation/source/history checks passed. All five jobs (including failures), four versions, 24 docs/two graphs and original ontology416 records/three versions unchanged. Fresh backup/rollback private under `.local/business-ontology/source-classification-20261101/`. Existing revision4 remains available; historical failures are not rewritten. See extraction-api.md and latest verification.

## Module generation controls — deployed 2026-11-01

Live build `8vqaj-Sh-UmNStQEmrsVU` fixes the owner's confusing generation display: selected-module latest result, exact-version/module draft navigation, explicit status refresh, separate history, retry and source import/save feedback. Regeneration receives required target IDs referenced by other modules; deterministic validation still rejects missing dependencies and now preserves safe actionable diagnostics. Historic organization failure remains honest; its exact old cause cannot be recovered from the generic stored error. No automatic model retry or new paid call.

62 backend, 236 relevant frontend and eight desktop/mobile browser checks passed; types/lint/build/contracts/OpenSpec passed. Live HTTPS desktop/mobile opened latest engine revision4 and historical3, read/imported existing source documents and checked refresh/form/retry controls without generation/cancellation/document-save actions. All four versions, 24 documents, two graphs and three jobs unchanged; original ontology416 records/three versions and credentials/config unchanged. Backup/rollback evidence private under `.local/business-ontology/generation-controls-20261101/`. See extraction-api.md and generation-controls verification. Broader unrelated workflow test failures and deferred individual login remain as recorded.

## Simpson reference-rule execution — deployed 2026-11-01

The three rules counted in Business Ontology now have actual deterministic execution handlers. Adds scoped immutable source-cited input revisions, evidence intake/history, a saved-graph rule runner, explained outcomes, calculations/provenance and exports. Root-cause findings, recurrence prerequisites and explicit cohort rates have complete/failed/unknown branches; matching quotations validate citations, not independent business truth. Reference-definition matching prevents arbitrary generated rules from becoming code. No SME gate, source/provider writes or new OpenAI call. Individual login remains deferred by owner.

Final live frontend `a7IU7JeJHO8dSVuERAul2`; existing shared-workspace authentication/config preserved. Backend 330, relevant frontend 233, staged browser16 plus final-copy4 passed; types/lint/build/contracts/OpenSpec passed. Three failures in unrelated workflow journey tests are recorded, not claimed fixed. Real HTTPS desktop/mobile verified all three handlers with missing-evidence outcomes and exports; both genuine graphs and original 416 ontology records/three versions unchanged. Positive source-cited cases and arithmetic verified in isolated tests; no synthetic conclusions seeded live. Fresh application/support/config backup and rollback artifacts retained privately. See `docs/simpson-business-ontology/rule-execution.md` and chunk15 verification. Follow-up is supplying actual source-cited case/cohort evidence through the implemented UI, not implementing missing handler logic.

## Next.js security patch — 2026-10-31

Owner-requested patch updates Next.js to exact 16.4.3 and its lockfile dependencies. Next.js audit entry and build warning are gone; zero critical findings remain. 106 frontend regressions, four isolated desktop/mobile ontology browser checks, types/lint/build/contracts/OpenSpec passed. Two obsolete metadata-rebuild tests were corrected without product changes. Other audit findings remain (12 moderate, two high in Vite and Zod); no blanket clean audit is claimed. Local only: live deployment/services/configuration/databases unchanged. Evidence: openspec/changes/next-security-patch/verification.md.

## Separate Simpson Business Ontology foundation — 2026-10-31

Chunk 2 implemented locally, not deployed. Adds independent business_ontology persistence, scoped/idempotent explicit binding of both owned Simpson sources, immutable foundation snapshot and three new business-ontology/v1 endpoints. Data Intelligence gains a separate Business Ontology tab with five-layer/twelve-module navigation, honest zero generated concepts/rules, viewer controls and loading/error handling. Uses SimpsonBusinessOntology names; existing BusinessOntology (Semantic Intelligence) and Ontology tabs preserved. No source/model calls, company writes, SME gate, runtime/shared-contract change or live initialization. 99 backend tests, 34 targeted frontend tests, two isolated desktop/mobile browser flows, types/lint/build/contracts/OpenSpec passed. Build tooling flagged an installed Next.js security advisory; no dependency changes. Evidence: openspec/changes/simpson-business-ontology/verification.md and docs/simpson-business-ontology/foundation-api.md. Next chunk is OpenAI extraction, not yet implemented.

## Ontology source-backed record explorer — 2026-10-31

Owner-authorized extension adds concept → source record → linked record browsing to Data Intelligence → Ontology. Existing query-reader/connector projection supports native IDs, safe approved scalar fields, scoped bounded paging and explicit reference/candidate/missing states; no source writes, new context/recovery engine or execution grants. Concept clicks open readable definitions and Browse records. Desktop/mobile record details, reference traversal, candidate invoice matching and existing management flows verified against isolated captures and the loaded live app. Details: `docs/ontology-review/simpsons/object-explorer.md`.

Frontend build `Luy8ChhV-XPO0tJlhuS7D`; published ontology `ov_3c9e855088f5ac678e11127661eae182b5189707`. Live drift was handled by audited technical revalidation of 150 unchanged approved definitions, preserving all 409 approved descriptions and seven drafts. Stale-version enforcement remains enabled; later real drift requires revalidation. 117 backend regressions, 51 final reader/query checks, 41 workflow/retrieval checks, 18 frontend/proxy tests, types/lint/build/contracts/OpenSpec and desktop/mobile browsers passed. 27 independently configured PostgreSQL fixture cases skipped in this run; no new live PostgreSQL acceptance claim. The native BSON decimal search fix received a separately approved backend reload. Rollback/approval/evidence remain private under `.local/ontology-foundation/object-release/`. Business SME acceptance/calibration remains task 7.3; no archive or contributor acceptance is inferred.

## Ontology business graph presentation — 2026-10-30

Corrected the owner-rejected technical ontology screen: default connected concept graph with real labelled relationships, overview/all-layer/search controls, readable fields/rules/source inspectors and explicit pending bindings. Existing review/publication management remains available. 19 UI tests, types/lint/build/contracts/OpenSpec, two management lifecycle browsers and captured/live desktop/mobile graph checks passed. Frontend-only build `zCmmvYM2O8OO6XuTavX-9` deployed with rollback and retained assets. Backend/worker PIDs, ontology/approval/version/evidence data, credentials, workflows and runs verified unchanged. Current ontology: 409 approved records, seven unresolved drafts; business calibration remains pending. Owner visual acceptance is still external to these checks. Evidence: `docs/ontology-review/simpsons/graph-ui.md`; private screenshots/checks under `.local/ontology-foundation/graph-release/`.

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


## MESH branding cleanup — 22 October 2026

Deployed frontend-only: MESH favicon, enlarged sidebar branding with Powered by PraxilonAI, sidebar creation shortcut removed, and only the two highlighted Google notices removed. Existing account controls preserved. Build/typecheck/lint, 77 tests and isolated/live desktop/mobile checks passed. No backend code/configuration or database changes; read-only before/after comparisons confirmed unchanged graph, connection IDs and workflow bindings. Evidence: openspec/changes/mesh-branding-cleanup/verification.md. Owner visual acceptance pending.


## Organization governance UI — 22 October 2026

Deployed three read-only Governance tabs: Organization Policies, Roles & Responsibilities, Oversight & Accountability. Document sections, session permissions and searchable runtime evidence replace draft editors/dashboard content on Governance only. Actual scope and missing organization information remain explicit; no fabricated policy, grant or audit data. Build/types/lint, shared contracts, strict OpenSpec, 76 tests and isolated/live desktop/mobile checks passed. Backend/configuration/database untouched; existing graph, connections and workflow bindings unchanged. Evidence: openspec/changes/organization-governance-ui/verification.md. Owner visual acceptance pending.


## Governance Usage & Limits separation — 22 October 2026

Deployed frontend-only replacement of Roles & Responsibilities with Usage & Limits. Organization Policies retains approvals/safeguards/access/data references; numerical boundaries now live only in the Execution/Delegation/Spending reference. Revision agent limits and runtime aggregate usage remain separate, with missing values/periods labelled and actual zero preserved. Expandable source details, revision selection, pagination and retrieval time included. No backend/API/configuration/database changes. Build/types/lint/contracts/OpenSpec, 77 tests and isolated/live desktop/mobile checks passed; workflow and graph bindings unchanged. Evidence: openspec/changes/governance-usage-limits/verification.md. Owner visual acceptance pending.


## Usage limit sample presentation — 22 October 2026

Verified maxChildren exists in the browser hierarchy editor and Builder.addChild; current monitoring does not report it. Retained the concept as Sub-agents per agent. Missing numeric Usage & Limits values now carry explicit Sample badges and a visible illustrative-data notice; real values and zeros remain unchanged. No samples enter runtime configuration or storage. Build/types/lint/contracts/OpenSpec, 77 tests and isolated/live desktop/mobile checks passed. Frontend-only deployment preserved backend processes, graph, connections and workflow bindings. Pending Monitoring/navigation changes remain unexecuted. Evidence: openspec/changes/usage-limit-samples/verification.md. Owner visual acceptance pending.


## Runs monitoring consolidation — 22 October 2026

Deployed frontend-only migration of standalone Monitoring into Runs. Four real API KPI cards precede existing run/reply controls; expandable runtime details retain usage, triggers, guardrails, audit, distribution, traces and pagination. Monitoring navigation/command/shortcut entries removed and old URL redirects to Runs. Approvals preserved throughout. Yellow Governance sample banner/badges replaced by a neutral example legend and starred illustrative numbers. Build/types/lint/contracts/OpenSpec, 90 tests and isolated/live desktop/mobile checks passed. Backend/API/configuration/database untouched; graph/connections/workflow bindings unchanged. Evidence: openspec/changes/runs-monitoring-consolidation/verification.md. Owner visual acceptance pending.


## Usage mock annotation cleanup — 22 October 2026

At explicit user request for a mock presentation, removed Usage & Limits asterisks, example legend, sample caveats and shared organization reference notice. Displayed numbers and interactions unchanged. Fallback values remain presentation mocks, not verified production measurements or enforced settings. Build/types/lint/contracts/OpenSpec, 77 tests and isolated/live desktop/mobile checks passed. Frontend-only deployment preserved backend processes, auth/connections, graph and workflow bindings. Evidence: openspec/changes/usage-mock-cleanup/verification.md. Owner visual acceptance pending.


## Operations stale-source recovery and Approvals navigation — 22 October 2026

Removed only shell Operate Approvals entry; approval pages/controls/other links preserved. Independently reproduced Operations 404 caused by an old policy connection ID absent from current owned connections. Minimal DataOperations.status patch omits only missing owned sources from discovery; context/action authorization remains strict and no policy grants are remapped. Live status now 200 with existing history and no current targets (explicit policy needed for new connections). Backend service restarted, worker unchanged. Config/policy hashes, connection/graph/workflow/refresh data preserved. 33 backend and 77 frontend tests, build/types/lint/contracts/OpenSpec, isolated/live desktop/mobile checks passed. Evidence: openspec/changes/operations-missing-source/verification.md. Owner acceptance pending.


## Editor preparation/run and policy guide — 22 October 2026

Deployed frontend-only Prepare & Activate / Activate changes plus active-version Run inside the editor. Exact saved/release reconciliation, sequential existing APIs, permission/approval pause, stop-on-error/edit, progress and explicit recovery preserved. Run retains input/idempotency handling, checks active release ID/version, then selects accepted run and opens Execution (including run-first procurement view). Governance placeholders replaced with approved imperative policy guidance and absent technical rows hidden; actual requirements/safeguards preserved. Mobile canvas toolbar no longer overlaps progress. Build/types/lint/contracts/OpenSpec and 115 tests passed; intercepted desktop/mobile lifecycle+Execution flows and read-only live checks passed. No real workflow activation/run or external action during verification. Backend/configuration/databases unchanged; source/graph/workflow bindings preserved. Evidence: openspec/changes/editor-launch-and-policy-guide/verification.md. Owner acceptance pending.


## PraxilonAI visible branding — 22 October 2026

Deployed frontend-only visible MESH→PraxilonAI branding across landing/login/app/title metadata/catalog publisher labels. Removed Powered by attribution and only the shared Knowledge sidebar/mobile-menu entry. Three-dot mark and Knowledge route/API/other access preserved; internal identifiers/storage unchanged. Build/types/lint/contracts/OpenSpec, 72 domain tests and isolated/live desktop/mobile checks passed. Backend/configuration/connections/workflow bindings unchanged. Evidence: openspec/changes/praxilonai-branding/verification.md. Owner visual acceptance pending.


## Data Intelligence notice removal — 22 October 2026

Removed only the requested shared-demo identity paragraph. All tabs/controls/backend behavior preserved. Build/TypeScript/lint, 78 existing tests and live desktop/mobile checks passed. Frontend-only deployment; auth/connections/graph/workflow bindings unchanged. Evidence: openspec/changes/data-intelligence-notice-removal/verification.md.


### Agent behaviour browser preferences — 2026-10-22

Deployed frontend-only Agent Behaviour & Safety inside Organization Policies: three groups, nine presets, eight switches, conditional language and explicit Apply with browser persistence. Manual changes show Custom; existing limits reference links to the same Usage & Limits tab. Exactly three tabs preserved. No runtime enforcement, agent/workflow payload, backend, database or contract changes. 79 targeted tests, lint/types/build/contracts/OpenSpec and isolated/live desktop/mobile flows passed; auth/connections/graph/workflow bindings unchanged. Evidence: openspec/changes/agent-behaviour-preferences/verification.md. Owner visual acceptance pending.


## Simpson Business Ontology chunk 3 — 31 October 2026

Implemented and verified locally, not deployed: scoped evidence documents, explicit existing-OpenAI generation jobs, validated source-cited draft definitions, immutable versions and source/version browsing in the separate Business Ontology tab. Existing Ontology and Semantic Intelligence preserved. No SME validation gate; candidate rules are non-executable. Current authorization, source/revision checks, idempotency and cancellation protect generation commits. Shared execution contracts unchanged.

Backend/source regressions (118 tests), final extraction tests (21, overlapping), provider/worker regressions (43), frontend regressions (110), types/lint/build, six desktop/mobile browser flows, shared contracts and strict OpenSpec passed. Owner explicitly approved one real warranty smoke test: 14 concepts, seven relationships, two draft rules on the configured OpenAI model. No company queries/writes, connector-secret transfer, live workspace mutations or extra real calls. Evidence and limitations: `openspec/changes/simpson-business-ontology/verification.md`; API handoff: `docs/simpson-business-ontology/extraction-api.md`. Next chunk: OWL/RDF and SHACL compiler with automated validation. No downstream acceptance or deployment is claimed.


## Simpson Business Ontology chunk 4 — 31 October 2026

Implemented and verified locally, not deployed: deterministic immutable-version OWL/RDF and SHACL compiler; offline structure/evidence, shape meta-validation and definition SHACL checks; scoped idempotent artifacts/audit; selected-version validation and six downloadable exports in Business Ontology. Existing Ontology/Semantic Intelligence and shared execution contracts preserved. No SME gate, company query/write, additional model call, rule execution or instance-validation claim.

Compiler tests (20), existing backend regressions (120), frontend regressions (115), domain tests (72), types/lint/build, eight desktop/mobile browser flows, shared contracts and strict OpenSpec passed. The earlier real-model warranty draft passed offline compilation (14 concepts, seven relationships, two draft rules; 525 ontology triples, 182 instance-shape triples), retaining 31 warnings. Company-instance validation and OWL reasoning remain not_run; business policy remains unverified. RDFLib/pySHACL dependencies added to root requirements and installed only in the local test environment. Evidence: `openspec/changes/simpson-business-ontology/verification.md`; integration/limits: `docs/simpson-business-ontology/compiler-api.md`. Next chunk: source-backed rule catalogue and competency queries. No deployment or downstream acceptance claimed.


## Simpson Business Ontology chunk 5 — 31 October 2026

Implemented and verified locally, not deployed: immutable-version rule catalogue with evidence basis, direct input attributes, source quotes/hashes and unresolved information; six bounded fixed read-only RDF SELECT queries on owned integrity-checked passing compilations; 22 blueprint business questions with explicit instance/policy/evidence prerequisites. Managers and viewers can query saved definitions; all candidates remain non-executable and business policy unverified. No auto-query/compilation, SME gate, company record query/write, model call or new query-history table.

168 backend tests, 195 frontend/domain tests, types/lint/build, ten desktop/mobile flows, shared contracts and strict OpenSpec passed. Browser tests exposed and verified fixes for duplicate panel keys after compilation and the catalogue retaining an old module filter. Existing Ontology/Semantic Intelligence and shared execution contracts preserved. Offline real-model draft yielded one implementation candidate and one proposed candidate, zero policy statements; all six queries completed with input/evidence/relationship/unknown results and no external calls or store writes. Evidence: `openspec/changes/simpson-business-ontology/verification.md`; API/limits: `docs/simpson-business-ontology/rules-and-queries.md`. Next: graph mappings and engine-to-monitoring path using both sources. Actual business-instance query templates/answers and policy decisions remain later work; no deployment or downstream acceptance claimed.


## Simpson Business Ontology chunk 6 — 31 October 2026

Implemented and verified locally, not deployed: explicit 21-collection source mapping catalogue, generated concept/attribute bindings, bounded two-source exact-serial graph builds, native typed record identities, direct references versus candidate serial/scope edges, unresolved/collection/truncation states, mapped RDF/SHACL validation and scoped immutable snapshots. UI includes explicit manager build/save, viewer historical inspection, mobile/desktop interactive graph, record/provenance inspection and RDF/report downloads. No semantic label inference, physical-engine merge, policy execution or company write; monitoring remains unavailable pending incorporation, confirmed comparable failures and exposure denominators.

187 broad backend tests plus final 20 graph tests (overlapping), 198 frontend/domain tests, types/lint/build, twelve browser flows, shared contracts and strict OpenSpec passed. Final phone graph readability rechecked. Real bounded invoice, ticket and QA paths used private isolated stores while live application metadata was opened read-only and credentials stayed in memory. Ticket path: four service records/four direct references/one candidate edge, zero mapped records so validation not_run. Final QA path: one invoice in db1 and one analysis in db2, one candidate serial edge, one mapped invoice record conforming. No matching claims fabricated; QA anchor-format skips and unavailable CAPA metadata retained. Company writes/model calls/live application writes/copied connector secrets zero; connector fingerprints unchanged. Failed initial QA diagnostic attempts are documented separately.

Evidence: `openspec/changes/simpson-business-ontology/verification.md`; API/mapping limits: `docs/simpson-business-ontology/source-graph.md`. Existing Ontology/Semantic Intelligence, source configuration and shared execution contracts preserved. Next: remaining modules and evidence-backed intelligence. Actual business-instance query answers and complete population/identity/monitoring semantics require adequate source/policy evidence. No deployment or downstream acceptance claimed.


## Simpson Business Ontology chunk 7 — 31 October 2026

Implemented locally, not deployed: curated source-quoted reference drafts for all twelve modules; explicit scoped add-missing-module immutable versions preserving existing definitions/history; versioned module/evidence/gap coverage and reference-origin inspection; six fixed source-qualified reports over saved graphs with record/field/hash citations, missing/truncated states, candidate/direct associations, bounded pages, source inspection and JSON page exports. No SME gate, model call, arbitrary report prompt/query, business-rule execution or warranty eligibility inference. Original Ontology/Semantic Intelligence and shared execution contracts preserved.

216 backend tests, 203 frontend/domain tests, final targeted UI checks, types/lint/build, fourteen desktop/mobile browser flows, contracts and strict OpenSpec passed. Previously saved real invoice/ticket/QA graphs were opened read-only: all report questions completed without fresh source/model calls, and adding eleven reference modules in memory preserved the actual 14 warranty concepts for 73 compilable concepts. QA report retained separate service/quality records with seven quality-field rows, three dated-field rows and 28 gaps. All tested saved graphs had zero claim observations; no missing claims or conclusions were fabricated. Input-store hashes unchanged, company/live application writes zero.

Evidence: `openspec/changes/simpson-business-ontology/verification.md`; API and limits: `docs/simpson-business-ontology/reference-and-intelligence.md`; reproducible read-only check: `scripts/check_business_intelligence.py`. Next work is authoritative policy/input applicability, physical-engine identity and monitoring evidence, followed by full instance competency/production acceptance. Those remain explicit unchecked tasks, not implied by twelve-module draft coverage. No deployment, live workspace initialization or downstream acceptance claimed.


## Simpson Business Ontology chunk 8 — 1 November 2026

Implemented and verified locally, not deployed: explicit saved-complaint warranty input preparation in the separate Simpson Business Ontology graph view. Preserves source fields/states/hashes, parses zero/nonnegative decimal hours and ISO dates, keeps complaint/alternate observations independent, shows separate invoice candidates with public-value serial/OEM comparisons, and retains policy/identity/assessment-time gaps as Requires Review with eligibility not_evaluated. Policy-kind documents and existing code/flags do not configure authority. Readers can prepare/inspect/export owned historical evidence; no company/model calls, automatic source reads, decision writes, new persistence table or SME workflow.

260 backend tests (44 new readiness checks included), 208 frontend/domain tests, types/lint/build, fourteen desktop/mobile flows, shared contracts and strict OpenSpec passed. Actual HTTP scope/origin/no-store and unchanged table rows checked. Previously saved real ticket graph yielded two independent cases with usable complaint sale dates/hours but no invoice/policy evidence; both stayed Requires Review. Invoice-only and QA graphs had no tickets and yielded no invented cases. Input-store hashes unchanged; credentials were not loaded and company/model/live-application writes/calls zero. Final desktop/mobile screenshots visually inspected.

Evidence: `openspec/changes/simpson-business-ontology/verification.md`; API/limits: `docs/simpson-business-ontology/warranty-readiness.md`; reproducible offline check: `scripts/check_business_warranty.py`. Original Ontology/Semantic Intelligence, connectors and shared execution contracts preserved. Complete applicable policy, identity, monitoring evidence and production competency acceptance remain open. Next: structured policy intake/applicability using authoritative source evidence; no deployment or downstream acceptance claimed.


## Simpson Business Ontology chunk 9 — 1 November 2026

Implemented and verified locally, not deployed: owner/workspace-scoped immutable source-cited policy draft revisions, guided policy-document/optional-clause intake, exact quotation/source-hash checks, explicit unknowns, current manager authority, atomic expected-revision CAS/audit and stable retry/concurrent-writer deduplication. Policy library supports historical evidence/exports and preserves immutable source metadata. No real Simpson policy seeded from implementation limits, flags or blueprint examples; no SME approval workflow, publication or executable policy state.

Saved-case comparison selects an exact policy revision, complaint, timezone-qualified assessment time and optional saved invoice, then compares literal OEM/model scope and declared effective-date basis/bounds only. Unknown end/basis/invoice/data remains unavailable. Outputs stay Requires Review, eligibility not_evaluated, policy authority unverified, physical-engine identity unresolved and limits/exclusions non-executed. Evidence and graph/definition/policy/source/result hashes are inspectable/exportable. No company/model call or decision write. Original Ontology/Semantic Intelligence, chunk-8 preparation, connectors and shared execution contracts preserved.

292 broad backend regressions passed; final policy suite passed 34 tests after blank/short citation strengthening (overlapping). Final frontend/domain suite 215 passed in 34 files; types/lint/production build, fourteen desktop/mobile flows, contracts and strict OpenSpec passed. Browser testing exposed and verified a fix for policy dropdown accessible names; source metadata export preservation has a regression. Final phone/desktop screenshots inspected. Actual HTTP covers session/origin/no-store, cited save/get/list, comparisons and foreign scope. Concurrent retries produce one policy revision/audit; comparisons preserve historical rows after connector disconnects.

Read-only offline inspection of three earlier private real graph stores found zero owned warranty-policy documents/revisions; ticket graph retains two complaints. No real policy comparison or eligibility was invented. Input file hashes unchanged; company/model/live application writes/calls zero. Evidence: `openspec/changes/simpson-business-ontology/verification.md`; API/limitations: `docs/simpson-business-ontology/policy-drafts.md`; read-only diagnostic: `scripts/check_business_policy_evidence.py`. Authoritative policy content/acceptance, verified policy-to-identifier and physical-engine mapping, structured executable exclusions/final eligibility, monitoring evidence and production competency acceptance remain open. No deployment, live initialization/service restart, extra model transfer or downstream acceptance claimed.


## Simpson Business Ontology chunk 10 — 1 November 2026

Implemented and verified locally, not deployed: corrected source-backed OEM namespaces (ticket.oem account, ticket.oemOrg company, invoice.oem company, account.oemNameId company). Warranty input readiness v2 compares invoice to ticket company and retains both ticket observations; existing policy draft v1 account-value semantics remain unchanged. Exact supplied model quotes/hashes and declared company/serial invoice uniqueness are retained as archive evidence, not deployed-index or physical-identity verification.

New graph mapping v2 retains native identifier tokens in hashed field projections, source-field edge annotations and bounded same-source account/invoice/company references. Company search values are typed/deduplicated before the twenty-value cap; clipped domains are marked truncated. Saved-ticket resolver/UI/API checks allowlisted paths, token/record integrity, company disagreement, typed serial/model candidates, multiple/missing invoices and distinct replacement observations. Legacy source edges remain saved/unverified-types; cross-source claims/QA are never merged. Requires Review, physical identity unresolved, no selected invoice and eligibility not_evaluated remain explicit where evidence cannot establish identity. No new identity table, approval workflow or business-rule execution.

311 backend tests, 219 frontend/domain tests in 35 files, types/lint/build, fourteen desktop/mobile browser flows, contracts and strict OpenSpec passed. Actual HTTP checks session/origin/no-store, malformed/foreign/non-ticket rejection and unchanged saved rows. Final screenshots inspected. Read-only previous real ticket graph yielded two complaints, each two retained legacy references, zero native-checked references and no invoice candidates; original invoice/QA graphs had no tickets. No invented physical identities or new real typed-source graph claimed. Input file hashes unchanged, company/model/live application writes/calls and identity merges zero.

Evidence: `openspec/changes/simpson-business-ontology/verification.md`; behavior and correction: `docs/simpson-business-ontology/engine-associations.md`; read-only diagnostic: `scripts/check_business_associations.py`. Original Ontology/Semantic Intelligence, connectors and shared execution contracts preserved. Authoritative stable identity/crosswalk/replacement-history evidence, policy/exclusion authority, monitoring/exposure and production competency acceptance remain open. No deployment, live initialization/service restart, extra model transfer or downstream acceptance claimed.


## Simpson Business Ontology chunk 11 — 1 November 2026

Implemented and verified locally, not deployed: deterministic three-outcome warranty kernel with strict unknown precedence; source-cited schema-v2 calculation conventions; explicit owned saved-case assessment with optional null policy, period/hour draft arithmetic, unknown exclusion findings, blocker/source/quote/provenance inspection and JSON export. Legacy policy revisions remain readable without inferred conventions. No public verification/input overrides, SME approval workflow, automatic invoice selection, alternate-hour substitution, company/model calls or decision writes. Current policy authority/applicability and physical identity remain unverified/unresolved, so current application cases correctly stay Requires Review even if draft limits pass or fail. All three final kernel outcomes are tested using trusted complete synthetic prerequisites only.

351 backend regressions, 224 frontend/domain tests in 36 files, types/lint/Next.js production build, fourteen desktop/mobile browser flows, shared contracts, strict OpenSpec, Python diagnostic compilation and diff integrity passed. Actual HTTP tests cover session/origin/no-store, selected/null policy, malformed/extra inputs, foreign scope and unchanged saved rows. Final assessment screenshots visually inspected. Original ontology/Semantic Intelligence, connector configuration and shared execution contracts preserved.

Read-only diagnostic on three earlier real graph stores produced two independent missing-policy Requires Review cases in the ticket graph, and no invented cases in invoice/QA graphs. No real policy or final eligibility fabricated. Explicit diagnostic timestamp is not a verified claim date. Input file hashes unchanged; company/model calls/writes and input-store writes zero. Evidence: `openspec/changes/simpson-business-ontology/verification.md`; API/calculation limits: `docs/simpson-business-ontology/warranty-assessment.md`; reproducible offline check: `scripts/check_business_assessment.py`.

Authoritative policy/applicability, stable physical identity and mapped exclusion evidence remain open data dependencies. Coverage supports explicit assessment-calendar-date basis only; failure-date semantics are not inferred. Next implementation area: monitoring prerequisites and evidence, followed by production competency/deployment acceptance. No live initialization, service restart, extra OpenAI transfer, deployment or downstream acceptance claimed.


## Simpson Business Ontology chunk 12 — 1 November 2026

Implemented and verified locally, not deployed: explicit saved-graph monitoring readiness with optional supported cut-in/QA/CAPA selection, inclusive calendar-date window, source-qualified observations, prerequisite matrix, source inspection, bounded pages and exact-page JSON exports. Source failure-date buckets are observations, not deduplicated failures. Selected changes do not establish cohorts, applicability, physical identity or incorporation; single hour readings do not establish longitudinal exposure. Recurrence/rate/effectiveness/population/exposure metrics remain null with evidence gaps. No serial ordering, raw flag approval/POST_CUT_IN inference, source/model calls, monitoring tables, alerts, scheduling or SME gate.

Final affected backend regressions: 374 passed in disjoint groups (125 + 249) after the initial combined process was terminated before completion. Final frontend/domain suite: 229 passed in 37 files, with a final five-test monitoring fixture recheck. Types/lint/Next.js production build, fourteen desktop/mobile flows, shared contracts, strict scoped OpenSpec, Python compilation and diff integrity passed. Actual HTTP covers session/origin/no-store, null/selected change, extra/malformed/foreign rejection and unchanged audit. Final desktop/mobile screenshots visually inspected. Existing ontology/Semantic Intelligence, warranty features, connectors and shared execution contracts preserved.

Read-only prior real invoice/ticket/QA snapshots yielded five/twelve/fifteen monitoring observations, respectively, with zero projected failure-date observations and all reliability metrics null. Explicitly selecting the QA change candidate exposed unverified applicability observations while incorporation, confirmed comparable failures, population and exposure stayed unavailable. Zero observations is not zero failures. Diagnostic dates are explicit test inputs, not an established monitoring period. All input hashes unchanged; no credentials loaded, company/model calls, company/input writes or monitoring schedules.

Evidence: `openspec/changes/simpson-business-ontology/verification.md`; API and limits: `docs/simpson-business-ontology/monitoring-readiness.md`; offline diagnostic: `scripts/check_business_monitoring.py`. Next: production-readiness/competency review and deployment preparation. Authoritative warranty/identity/exclusion and monitoring cohort/incorporation/comparability/exposure data dependencies remain open. No live workspace initialization, service restart, extra OpenAI transfer, deployment or downstream acceptance claimed.


## Simpson Business Ontology chunk 13 — 1 November 2026

Completed locally: offline release audit, all 22 competency non-acceptance/gap mappings, private owned ontology-artifact recovery and deployment/rollback runbook. Ten fixed table/column schemas, consistent read-only bounded extraction, source/draft/compilation/graph/policy/head integrity and recovered row/report hashes checked. Job states and the one-active-job uniqueness index preserved without application/worker startup or model replay. Source/dependency manifests contain hashes/versions, not environment secrets. Recovery excludes credentials, keys and other application tables, so it is not a full application backup acceptance.

115 related release/security/compiler/monitoring/policy checks passed; final 16-test audit suite passed after strengthening (overlapping counts). Shared contracts, strict OpenSpec, Python compilation and diff integrity passed. Frontend/runtime product code untouched this chunk; prior frontend/build/browser evidence is not live acceptance. Three earlier real saved stores passed final recovery with one/four/two records, zero policy revisions and zero accepted competencies; monitoring report hashes matched, inputs unchanged, source/model calls/writes and services started zero. Private reports: `.local/business-ontology/chunk13-final-{connector-check,ticket-check,quality-valid-anchor}/`.

Public release remains not_ready: current backend production mode intentionally rejects startup because trusted production login is deferred. The shared frontend access cookie is not individual backend production authentication. Live HTTPS/roles/tenant tests, target worker/storage behavior, complete encrypted credential/key-backed recovery and actual business competencies remain unverified. Do not bypass the code gate, expose development sessions, attach the offline archive to a running service or replay uncertain jobs.

Review: `docs/simpson-business-ontology/release-preparation.md`, `competency-acceptance.md`; detailed evidence: `openspec/changes/simpson-business-ontology/verification.md`; repeatable CLI: `scripts/check_business_release.py` (exit 2 completed/not-ready, 1 unavailable). Next prerequisite is trusted production authentication and target acceptance, alongside authoritative business data. No deployment, live ontology initialization, service restart, credential/config change, SME workflow or extra OpenAI transfer claimed.


## Simpson Business Ontology chunk 14 — 1 November 2026

Owner explicitly deferred individual login and authorized backup/recovery plus existing shared-workspace activation for functional testing. Completed and active: full application SQLite backup (83 tables), three supporting databases/artifacts, required encrypted-credential/key/config/service copies and source/frontend rollback artifacts; isolated restored API/integrity checks and credential decryption (2 source, 4 Google) passed without network/workers. Private root: `.local/business-ontology/live-rollout-20261101/`. Supporting stores are individually consistent, and this is not an off-host/external-provider recovery claim.

Staged Next.js build passed fourteen desktop/mobile flows, then build `Bl1WZvbmZJ-iK9fyeGHGt` was activated, retaining 67 prior static files. Builder backend/worker/frontend restarted after confirming no queued/running work. Current worker active; private backend/UI ports 8002/3001 and existing shared login/config/origins unchanged. Generation configured, zero jobs submitted by verification. No production-auth bypass or new individual login implemented.

Separate live Business Ontology initialized with both Simpson sources: 67 source-cited reference concepts, 14 relationships, 3 non-executable rules across twelve modules, compilation passed. Real complaint graph has four service records/two complaints/two mapped records; invoice/QA graph has two service and one quality record with a candidate association. Both validations passed. Actual saved-case APIs and desktop/390px mobile HTTPS login/graph/readiness/assessment/export/monitoring/original-tab checks passed; zero page errors/overflow/unexpected mutations. Missing policy correctly Requires Review; recurrence/rates remain unavailable. Screenshots inspected.

Original ontology record/version payloads preserved (416 records/3 versions); connector ciphertext and backed-up config hashes unchanged. Bounded source reads only, no company writes, model calls, email or workflow invocation by this rollout. User can inspect https://praxi.bellcorpstudio.com/app/data-intelligence → Business Ontology now; select a saved graph to view evidence. Individual production login and authoritative business-data prerequisites remain deferred/open. Details: `docs/simpson-business-ontology/functional-rollout.md`; complete evidence: `openspec/changes/simpson-business-ontology/verification.md`. Preserve additive histories on any rollback; do not overwrite subsequent live work with the older full backup.


## Automatic Simpson Business Ontology planning — 1 November 2026

Owner-authorized integration is implemented and deployed in build `8XcKU7N-zHUG4DMKasjp4`. Overview workflow generation automatically retrieves relevant owned Business Ontology definitions and latest policy interpretations; canonical planning validates exact action-step references and saves server-owned provenance. The editor exposes **View ontology evidence**, source quotations, exact version/hashes and export. Save verification rejects altered/foreign traces. Existing retries pin evidence; fresh generation sees newer versions. Source retrieval is bounded/read-only and no model selection pass, SME gate, execution permission or business approval is added.

197 distinct scoped backend cases, 25 frontend tests, four desktop/mobile create/save/evidence browser flows, build/types/lint/contracts/strict OpenSpec and one explicitly approved configured-model planning test passed. Live HTTPS preservation checks passed; no company writes or workflow executions occurred. No full-suite green or downstream contributor acceptance is claimed. See `docs/simpson-business-ontology/workflow-planning.md` and `openspec/changes/business-ontology-workflow-planning/verification.md` for exact coverage, existing unrelated assertions, live evidence and limitations. This is a repository handoff, not an external notification.


## Automatic source pool size correction — 1 November 2026
The reported Simpson generation failure KG_RETRIEVAL_LIMIT is fixed and deployed. Automatic retrieval now packs complete ranked schemas within the existing 70 KB budget, filters references to fitting sources and discloses omissions; explicit selection and four-source execution limits remain. Exact suggested prompt reproduced against saved live metadata: 11 sources/54,479 bytes, business revision 4, valid local fixture proposal. 75 scoped backend tests passed; service and ontology/library health checks passed. No new OpenAI success is claimed. See `openspec/changes/bounded-planning-source-pool/verification.md`.


## Business planning binding reliability — 1 November 2026
A newly approved real hierarchy diagnostic succeeded on its first configured-model call; earlier rejected draft shapes were not retained, so their exact defect is unknown. Explicit model-request binding schema, hierarchy targeting guidance, unambiguous grounded normalization with audit, and precise bounded correction feedback are now deployed. 77 scoped backend tests and captured-output replay passed. Actual captured draft `planned_d365b41086457927` was saved through normal API with server-owned ontology evidence, unapproved/unpublished/unexecuted. See `openspec/changes/business-planning-binding-reliability/verification.md`; this is not a claim that the original failed job succeeded.


## Generic wide-schema source binding fix — 1 November 2026
The inspection planner path accepted ~48 KB of field metadata but rejected it at a later 16 KB agent-reference boundary. Generic bounded task references now preserve exact selected sources and task-relevant fields with omission counts; full runtime schema/authorization validation remains. Specific source-binding feedback and model-request source-ID enums replace ambiguous correction hints. No Simpson prompt template or arbitrary source substitution was added. 133 scoped backend tests passed. Exactly three newly approved real configured-model generations succeeded on first attempts (exact investigation prompt, warranty prompt, investigation paraphrase), each with ontology contributions. Deployed backend/worker; frontend/configuration/saved business artifacts preserved. No workflow execution or prepared draft substitution. See `openspec/changes/planner-database-binding-reliability/verification.md`.


## Business workflow review clarity — 1 November 2026
Deployed build `pjXXWUjk41Hu8X1BkOlR1`: business definitions and workflow contribution first, sources/technical hashes optional, modal opens at its heading. Conservative no-input read-only coverage classification preserves original text/audit and does not remove real required setup. The affected `planned_519c982f6efc08bd` was repaired through normal API as v2, validated and submitted with Registry ready, while v1 and exact ontology trace are preserved. No approval/publication/activation/execution or model calls. 85 distinct scoped backend tests, 20 frontend tests, four staged desktop/mobile flows, build/types/lint/contracts/OpenSpec and actual API readiness checks passed. See `openspec/changes/business-workflow-review-clarity/verification.md`.


## Investigation workflow UI — 3 November 2026
Deployed at https://praxi.bellcorpstudio.com/app in build `ZOf2NBddrsZM1RGAcDDhL`: Overview prompt routes supported requests to a saved branching investigation graph, explicit Run, actual node/edge states, node records, source-backed report, typed input/resume/cancel and optional ontology evidence. Existing general automation remains available. Durable owner-scoped jobs run in the existing worker service with current authority and no automatic paid replay.

Live knowledge revision 7 was explicitly imported after a restored-database preflight; earlier snapshots/policies/connections/configuration preserved. Real HTTPS acceptance for A-2022-12-013 completed with gaps: 18 nodes, two unique records, three CrewAI analyses and 25 validated findings. An initial invalid citation was rejected and preserved; bounded citation catalogs/request-specific schemas and correct nonretryable Start new run recovery were added before final acceptance. No company writes or general workflow dispatch.

455 frontend tests, 131 distinct scoped backend cases across overlapping runs, four desktop/mobile fixture flows, live authenticated node/report/source/refresh/mobile checks, types/lint/build/contracts/OpenSpec passed. Private backups/receipts: `.local/investigation-ui-rollout-20261103/`. Operational details and limits: `docs/simpson-business-ontology/investigation-workflow-ui.md`; exact coverage: `openspec/changes/investigation-workflow-ui/verification.md`. Saved evidence follows existing persistence; authoritative policy/identity gaps and individual production login remain separate dependencies. This is an in-repository handoff, not an external notification.


## Connected evidence coverage — 4 November 2026 (local handoff)

Ready for handoff, not downstream acceptance. Added reusable typed evidence providers, scoped immutable connected-case environments/manifests, signed preflight and runtime source/withdrawal revalidation through the existing Phase 3 service. New UI/API/jobs/CLI preparation uses initial evidence coverage; reports distinguish execution, mandatory decision blockers and optional limitations. Shared workflow/agent/tool contracts and historical runs remain unchanged.

Two independently checked source cases underpin 24 isolated scenarios and 72 task validations for comparison, configured warranty assessment and replacement review. All 24 workflows completed in explicit offline diagnostic mode; missing/conflicting variants retain expected blockers, negative decisions are known outcomes, generated events remain distinguishable from captured observations. No claim of company authority or live model quality. Broad relevant backend 742 passed, follow-up scoped 69 passed and final provider/environment 28 passed (overlapping counts); frontend 456 passed, browser eight passed; types/lint/staged build/contracts/drift/strict scoped OpenSpec passed. No deployment, restart, live import, company writes or new paid calls. Live website remains the previously deployed version.

Exact terminal commands, source/scenario boundaries and file/report inventory: `docs/simpson-business-ontology/evidence-coverage.md` and `openspec/changes/business-evidence-coverage/verification.md`. Further QA/CAPA/operational business events need separate contracts/evidence. This is a repository handoff, not an external notification.


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


## Persistent lifecycle UI — 4 November 2026

Integrated Phase 4–6 cases within existing Workflow → Business Investigation and
existing investigate route. Pinned stages, real compositions/receipts, provenance,
waits, memory/recovery/reassessment and qualified reports use backend authority.
Normal workflow/action approvals remain required. Explicit uncertain retries keep
identical request keys; revisions and tenant/owner isolation are enforced.

480 frontend tests, types/lint, production build, 12 desktop/mobile browser tests,
79 Phase 4–6 backend regressions plus two scoped-index tests passed. The actual
browser lifecycle checks used disposable storage and bounded deterministic model/
evidence transports with real CrewAI/Registry/runtime, with no live effects.

File inventory, API mapping and acceptance/deployment details:
`docs/simpson-business-ontology/business-lifecycle-ui.md` and
`openspec/changes/business-lifecycle-ui/verification.md`.
Deployment status is recorded in that verification file. Internal repository
handoff only; no external contributor messages were sent.

Final lifecycle UI deployment verified: build `RUVN4lBRiT8k8fJPZK96M` at
https://praxi.bellcorpstudio.com/app. All existing services active; normal public
login, case/create/reopen/report/cancel, twelve stages, memory/recovery, existing
navigation/composition and desktop/mobile passed with zero browser/asset errors.
170,531 original rows across 32 tables matched before intentional labelled smoke
cases; both smoke cases were cancelled without execution. Lifecycle migrations
1/2 verified. No paid calls or live connector effects. Private rollback artifacts
and receipts: `.local/business-lifecycle-ui-release-20261104/`.


## Gmail-only business investigation setup correction

Fixed false SIDE_EFFECT_MISMATCH for standalone Gmail drafts when the deployment
uses automatic procurement connectors. Planning now shares runtime's standalone
write classification; normal destination/schema/permission checks and exact action
approvals remain. Multi-action UI/web-search are unchanged. Tests caught and fixed
an eager metadata access regression on legacy row connectors before deployment.
Final affected suite: 65 passed. Existing backend/worker correction deployed;
170,591 rows across 32 tables preserved. Normal authenticated public planning with
saved user inputs verified ready, zero model calls/external actions; original
failed workflow retained. Generate an updated workflow to use the fix.
Evidence: `openspec/changes/business-draft-connector-binding/verification.md`.


## Subway report reliability and workflow card layout — 12 November 2026

Subway-only deployment reduces report transport with reversible shared evidence/tables, preserves typed model failures and safe diagnostics, corrects misleading recovery guidance and bounds workflow cards to actual layout dimensions. Original evidence and full instructions remain; no external action was repeated. See `openspec/changes/subway-report-reliability-layout/verification.md` for exact tests, deployment and the unresolved historical provider-cause/live-provider acceptance boundary. Simpson services and records are unchanged.


## Natural email and Calendar review — Simpson and Subway, 12 November 2026

Deployed tenant-isolated owned-account/primary-calendar resolution, structured natural send/draft and timing choices, plain-language review, pinned after-ready/fixed times and provider-confirmed independent statuses. Expired undispatched Calendar actions support separately approved Calendar-only continuations; confirmed email remains unchanged, unknown writes stay reconciliation-only. 53 backend tests per candidate plus final six exact natural cases per tenant, 60 affected regressions, 23 frontend tests and 20 desktop/mobile journeys passed (overlapping). Existing data/configuration/schedules preserved; no live communication or schedule creation. See `openspec/changes/natural-email-calendar-review/verification.md` for exact boundaries and rollout details.
