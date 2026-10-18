# Handoff — Rethika

## Unchanged model settings and concise inventory planning — 2026-10-18

The UI added temperature:0 while saving generated models that omitted it,
causing exact Registry configuration mismatch. Mapping now preserves omission
for unchanged model/default values; explicit edits remain subject to review.
The short Google Sheet prompt also missed the inventory compiler's spreadsheet
wording. Compiler accepts both forms and unambiguous exact IST intervals without
redundant duration; flexible windows still require a duration. No Registry rule
was bypassed. The affected draft was recovered as validated revision 3 through
normal APIs without approval/publication/execution. See preserve-agent-settings
OpenSpec tasks for test evidence and the unrelated empty-catalog test failure.

## Inline Execution approvals — 2026-10-18

ExecutionView now shows all matching pending approvals for the selected paused run,
including spreadsheet, email and calendar gates. Reuses ApprovalControl, server
permissions, exact revision bindings and database review requirements. Decisions
refresh the trace. Terminal runs and mismatched approvals have no inline controls.
32 focused tests, build, types, lint and desktop/mobile browser checks passed;
browser decisions were mocked. Frontend deployed; backend contracts unchanged.

## Shared validation feedback — 2026-10-18

Added a small shared feedback helper and one correction around pure runtime model
calls: coordinator control, specialist tool/task decisions and ordinary agents.
Safe codes/hints and available schemas guide correction; task/tool inputs are
validated before dispatch. Exact Registry authorization and action approvals remain
authoritative. Correction reserves a fresh call, rechecks run/revision/deadlines
and records agent.correction. Invalid second output stops. Reviewed allowances
are not expanded, and failed-call reservations remain conservative. Tools,
permissions, provider errors and uncertain external writes are never replayed.

Planner generation retains two attempts, enriched with actionable recipient/cost
rule hints and a secret-checked prior draft. JSON and missing hierarchy output
errors now enter that same bounded correction loop. No shared contracts changed.
135 regression tests and 25 subtests passed, plus targeted ordinary-agent and
real CrewAI/model-bridge correction checks. Contracts, scoped strict OpenSpec and
diff checks passed. No live generation or Google actions were used for verification.
Deployment evidence: `openspec/changes/simple-llm-feedback/tasks.md`.

## Meeting-window wording — 2026-10-18

REPORT_MEETING_TIME_REQUIRED from the supplied "within 3:00–4:00 PM IST"
prompt was caused by requiring literal "from" in meeting_window. The parser now
accepts from/within/between and dash/to/and separators, retaining explicit date,
duration, IST and window validation and final fitting slot preference.
21 planner tests pass, including equivalent wordings, invalid windows and compiler
generation with the supplied wording. Contracts, strict scoped OpenSpec and diff
checks pass. No workflow or Google action was executed for this fix.

## Per-action report identity — 2026-10-18

Live run `run_5a32f33c84674e3984ea1cbf322951d8` completed research, ranking
and spreadsheet approval, then failed create_report with EFFECT_REFERENCE_MISMATCH.
The journal contains a completed report under the compiler's fixed project/key;
its report hash differs from the fresh findings. Report exports inherited permanent
setup's cross-run identity, incorrectly treating a new report as a mutated old one.

ReportSheetsSetup now scopes its stable effect to the bound workflow namespace
and runtime action reference, keeping project/key and fingerprint checks. Same
action retries reuse verified receipts; fresh runs create distinct reports.
Permanent setup, old receipts, uncertain-effect checks, approvals and input
validation are preserved. Reconciliation accepts the original effect_id; omitting
it retains legacy receipt lookup. Mail and Calendar already use runtime effect IDs.
See `openspec/changes/report-action-identity/` for verification and deployment.

## Inventory research result handoff — 2026-10-18

Live v2 run `run_175e1144d3b249fe87a85e9828a42b95` failed on the second
coordinator call while its helper was pending; research subsequently completed
with valid output. Compiled inventory reports now wait for their sole research
child and forward its matching validated output without a redundant coordinator
model call. General workflows retain model synthesis. Cancellation, failure,
schema validation, authorization and all three Google approvals remain enforced.
The existing v2 meets the narrow compiler/schema/capability conditions; no saved
revision was modified. Unseen failed provider text is not claimed diagnosed.

8 inventory runtime tests and 43 planner/protocol/delegation tests plus 7 subtests
passed. Shared contracts, strict scoped OpenSpec and diff checks passed. Full live
Google execution remains unverified. See `openspec/changes/inventory-research-handoff/`.

## Operator usage-budget override — 2026-10-18

Added trusted launcher setting `BUILDER_ENFORCE_USAGE_BUDGETS` (default `1`).
The operator requested backend usage-cap removal; this deployment now sets `0`.
Cumulative workflow/agent token and estimated-cost caps no longer stop execution.
Each model turn retains finite token capacity, and call counts, delegation bounds,
timeouts, retries, Registry/schema checks and Google approvals remain enforced.
Confirmed cost above a disabled cap remains finite and correctly accounted.
No shared contracts or reviewed workflow revisions were changed.

115 runtime/delegation/live-provider tests passed; two final targeted tests passed
after finite-value validation tightening. Contracts, strict scoped OpenSpec and
diff checks pass. Backend and worker reloaded; session/worker-health returned 200
and current RuntimeWorker is ready. No inventory workflow or Google action was
executed for verification. Start a new run of the existing published release;
full live execution is not yet established. See `openspec/changes/optional-usage-budgets/`.

## Google consent diagnostics — 2026-10-12

Remote OAuth setup now offers account selection and credential-free actionable errors. Scope-change responses are accepted only if all configured permissions are covered (Sheets write includes Sheets read); denied permissions or absent offline access preserve the old token. Actual grants are persisted privately. Eight focused OAuth tests, shared contracts, strict scoped OpenSpec and diff checks pass. Live consent remains pending; the saved token has no Sheets edit scope. No user credentials, workflows or backend processes were changed. See `openspec/changes/google-oauth-diagnostics/` and the remote command in `docs/sheets-gmail.md`.

Alternative added after the browser remained on Google's consent page: `--paste-refresh-token` imports a hidden refresh token from Google OAuth Playground using the configured client's credentials. Actual Google refresh response scope evidence is mandatory; the old token is preserved on failure. Ten focused tests pass with mocked transports, including the real refresh parser. Operator must add Google's Playground HTTPS URI to their web client's redirect list and complete consent; neither client settings nor live tokens were changed here. This alternative does not bypass Google consent or prove the original browser failure's cause.

Refresh failures now display only allowlisted structured Google error categories, including invalid_rapt session-policy subtype, and reject plainly wrong paste formats. Redundant Sheets readonly is omitted from refresh requests when Sheets write is configured; validation still requires all original permissions. Thirteen focused tests pass. Live dummy-token diagnostic returned invalid_grant rather than invalid_client; no actual user-token refresh or permission validation is claimed. Saved credentials were unchanged. User must retry the hidden import and provide only the safe categorized error if it fails.

## Restaurant generation failure recovery — 2026-10-12

Live diagnosis reproduced an OpenAI timeout mislabeled INVALID_API_DATA. Planning now has an explicit bounded 180-second default deadline, preserving runtime timeouts/zero retries, and SDK failures return safe retryable planner errors. Captured real model drafts also exposed mixed literal/dynamic configurations and omitted closed save-field schemas. Fresh proposals normalize disjoint supported literals into one mapping and tighten omitted extra-property restrictions for explicit save-field schemas; ambiguous/unsupported inputs and explicit open schemas are not guessed. Exhausted correction reports structured requirement codes. Existing saved-workflow execution semantics are preserved.

226 Python tests, shared contracts, generated-client drift and strict OpenSpec pass. The actual captured model draft passed corrected generation and save in isolated storage; no fresh post-fix live model success or live workflow execution is claimed. No Sheets writes, emails, publication or credentials changed. The requested backend reload was rejected, so the operator must restart their running backend and refresh the UI. Evidence and limits: `openspec/changes/planner-timeout-errors/tasks.md`.

## Prompt-owned Sheets destinations — 2026-10-12

Supersedes the mandatory environment target setup in the original Phase 1 note below. Generated workflows now save `metadata.sheet_write_targets` from the UI setup prompt. The live planner exposes record writes without an environment destination list; publication validates the metadata and graph mappings, and the shared graph/delegated tool boundary binds a restricted connector to the exact reviewed revision. Optional environment targets only narrow access or support legacy workflows. The editor shows spreadsheet IDs, ranges, writable columns and record-creation permission before publishing. Google write consent and the separate automatic-write opt-in remain one-time backend setup.

Verification: 221 Python tests, 90 frontend tests, types, lint, production build, two desktop/mobile Playwright checks, shared contracts, generated-client drift, strict OpenSpec and diff checks passed. Tests use offline providers and mocked browser API responses; live accounts and deployments are not claimed verified. No credentials or user sheets were changed. See `openspec/changes/prompt-owned-sheet-access/` and the revised `docs/sheet-drafts-phase1.md`. Existing v1 schema/grant shapes remain unchanged; prompt-supplied business roles are not hardcoded.

## Generic Sheets draft automation, Phase 1 — 2026-10-12

Added `google_sheets_upsert_record` through the existing `update_spreadsheet` capability and live Registry/connector map. Server-owned target/range/ID/column policies and a separate `BUILDER_SHEETS_DIRECT_WRITE` opt-in restrict automatic writes. The prompt-driven planner retains generated master/specialist roles, receives the actual record schema and authorized target configuration, and maps validated final outputs into deterministic save steps. Generation, validation, review/publication and activation check graph save destinations and scalar output schemas. Existing versioned contracts, read polling, email policy, budgets and communication traces are preserved.

217 Python tests pass; final focused planner/approval checks pass; shared contracts, generated-client drift, strict OpenSpec and diff-format checks pass. The 18 new test methods include offline actual planner/Registry/publication/polling/CrewAI/connector execution for restaurant and manufacturing, approval pauses, missing/ambiguous evidence, sorted/offset rows, concurrent saves, restart deduplication and partial failure. These results do not establish live Google access or live model accuracy. No user credentials, live sheets, workflow database or running backend were changed.

Setup, example prompts and deployment limits: `docs/sheet-drafts-phase1.md`. OpenSpec delivery/evidence: `openspec/changes/generic-sheet-draft-automation/`. Operator target configuration, Google edit consent, restart and a reviewed generated workflow are needed for live use. Local file locks coordinate cooperating processes only; external editors and separate hosts can race, and multiple target saves are not atomic. Inbox reading and email delivery remain later phases.

Repository handoff for Suprajha (planner context/schema), Aravind (new tool and restricted destinations), Harihar (existing publish/validation UI) and Rethika (connector/runtime behavior). No external messages or owner acceptance are claimed.

## Delegated connector access — 2026-10-11

Dynamic subagents can now call their exact reviewed Registry tools through a bounded application-managed decision loop, receive actual connector output and return findings while the master continues independent work. Graph and delegated calls share authorization, schema, approval, timeout and budget checks. Dynamic read tools remain inside specialist tasks rather than becoming fixed reads after the master. The communication view shows delegated connector calls and result handoffs.

Verification: 190 Python tests, 80 frontend tests, production build/types/lint, shared contracts, strict delegated-tool-access OpenSpec validation and two desktop/mobile browser checks pass. Actual bounded CrewAI and GoogleSheetsConnector are exercised using offline model/OAuth/HTTP responses, including a contradicted claim, access denial, revocation, cancellation and exhausted budgets. No live Google read, backend restart, credential change, publication or external write occurred. The configured live backend's existing connector map is reused; it must load the new code for running instances to use this path. See runtime/README.md and openspec/changes/delegated-tool-access/ for protocol, limits and evidence.

## Live delivery recovery — 2026-10-10

Generic worksheet recovery: the new Tickets workflow planned_82b3260b91547770 failed because its document title Tickets was used as a tab name while the actual tab was Sheet1. On an invalid named range, the reader now checks metadata and uses the sole actual worksheet only if the requested name is absent. Multiple worksheets fail clearly with SHEETS_RANGE_INVALID. Header/identity/authorization and baseline checks remain enforced. Baseline was established and an explicit test of existing T002 completed in run_36580e6d169447a192e350531acc0b82 with two actual model calls, one tool call and confirmed SMTP submission. No worksheet writes or business-rule changes were made. All 151 Python tests, contracts and strict OpenSpec pass; tests cover sole-tab recovery, ambiguous-tab rejection and access-denial preservation. The operator must restart their existing backend for ongoing polling to load this change.

The current direct-send workflow planned_8edc186ab6296f36 had source error EVENT_MAPPING_FAILED because priority used row["priority"] and the previous mapper supported dot paths only. Data-only literal bracket paths are now supported, and workflow publication validates their syntax. The retained checkpoint was retried through the published workflow without starting another backend or replacing its release. Runs run_022cc20961694b9f944a698da5acfde3 and run_6692ed838e554157b6bd1b8feff40fe8 each completed with two real model calls, one email tool call and a confirmed SMTP message ID. SMTP recipient acceptance is verified; inbox placement is not. The old disabled workflow's pending approval remains historical and was not bypassed.

Monitoring aggregates workflow reservations once instead of also summing the agent copies. Its workspace-scoped response adds source/baseline/checkpoint health, reviewed agent guardrails and safe runtime audit references. Governance's default live panel consumes the same server endpoint; local draft policy controls remain separately labeled. Python tests (148), frontend tests (66), types/lint, contracts, strict OpenSpec and four isolated desktop/mobile browser checks pass. An operator restart loads these changes into the existing backend for future events.

- **Segment:** Runtime and observability, including the planned published workflow lifecycle.
- **Status:** ready-for-handoff — core runtime and the accepted lifecycle/trigger extension are implemented; final verification evidence is recorded below.
- **Contract versions:** workflow-schema-v1, agent-contract-v1, tool-contract-v1, api-payloads-v1, error-format-v1, auth-permissions-v1, branching-approvals-v1, run-status-versioning-v1, and additive workflow-operations-v2. All four owners unanimously accepted v2 on 2026-10-10; v1 was not extended.
- **Completed work:** Approved revision/auth/provenance/grant checks; durable idempotent runs and canonical events; actual CrewAI construction/execution with bounded model bridge; deterministic branches/joins; approval decisions/rejection/timeout paths; cumulative budgets; credential-reference SMTP adapter; interrupted-call denial; trusted worker identity resolution; redacted OTel export. Existing runtime API routes are opt-in connected. See `runtime/README.md` for exact configuration and limits.
- **Verification evidence:** Fresh evidence and commands are recorded in the implementation review below; all earlier upstream implementation evidence remains attributed to its owner.
- **Known defects / limits:** Production auth/PostgreSQL and live provider quota reservation remain absent. Upstream external-write publication approval integration remains unavailable. Default dev runtime has no model/connector adapter or automatically started worker. Tests use offline model/SMTP transports, not real email delivery. Generic signed webhook is the only real incoming transport; provider-specific subscriptions, poll clients, and cron calculation require operator adapters. Basic redaction/injection detection is not exhaustive.
- **Dependencies:** Suprajha's canonical drafts; Aravind's current exact assignments, policy/scopes/credentials and approval evidence; Harihar's exact approved revisions and trusted API/auth boundary. Rethika explicitly accepted their delivered boundaries in this session; unfinished upstream integration is not claimed complete.
- **Downstream consumers:** Harihar for runtime/approval DTO wiring and remaining UI tasks; Aravind for authorization/approval and restart review; Suprajha for executable expression/input mappings; cross-segment POC integration and operational consumers for run/trace/connector evidence.
- **Unresolved decisions / blockers:** No blocker remains for the accepted local POC. Production authentication, external provider setup, retention duration, distributed workers, and external-write publication approval are deployment work outside this change.
- **Next actions:** Review the recorded evidence and archive the OpenSpec change after acceptance. Operators may then configure production auth/storage and explicitly authorized provider adapters without broadening the accepted capability inventory.

## Aravind registry delivery — 2026-10-09

Suprajha’s planner handoff was explicitly accepted by Aravind. Registry implementation and local verification are complete: 35 tests passed; shared contracts valid; strict registry OpenSpec validation passed. Read `docs/contributors/handoffs/aravind.md` and `docs/contributors/examples/aravind-registry.json` for the complete service boundary, authorization policy, safe metadata, assignment bindings, and limitations. Your downstream review is required before Aravind task 4.4 can be completed. This file records notification, not your acceptance.

Consume only authorized assignments for approved workflow revisions and revalidate their exact subject/workspace/workflow/agent/tool/version binding before execution. Pending approvals have no executable grants. Registry authorization records are process-local; refresh quota/credential policy and enforce runtime budgets in your segment.

## Harihar UI/API delivery and review request

Harihar delivered canonical workflow loading/saving/versioning, planner draft rendering, safe errors, server-configured local development sessions, registry discovery and gated deterministic revision approval/publication. No runtime, connectors or workflow gate decisions were implemented. Read [Harihar API boundary](../harihar-api.md) and `docs/contributors/handoffs/harihar.md` for the exact routes, DTO projections, UI availability states, verification evidence and eight execution-input groups.

Review the exact approved workflow revision, trusted auth boundary, Aravind assignment revalidation, execution idempotency envelope, run/event/approval DTOs, legal run observations and hierarchy mapping before connecting execution. Runtime/approval endpoints currently fail unavailable; the UI does not fabricate runs or grant pending approvals. Global run/approval collection operations are absent from the accepted operation-name contract and need shared-owner agreement. Production login and PostgreSQL remain separate from Harihar's local POC session/SQLite adapters.

This is a repository review request and partial upstream delivery, not your acceptance or a ready-for-execution claim. Harihar's full AI-workflow publication in task 2.2, tasks 3.1–3.3 and 4.4 remain open until the live dependency boundaries and your review are delivered.

### Updated Harihar registry/publication handoff

This supersedes the missing assignment-integration and task 2.2/3.1 statements above. Harihar now delivers explicit trusted registry configuration, exact agent matching, authorized assignment/revalidation, safe UI assignment states and publication gating. Tasks 2.2 and 3.1 are complete; 10/13 Harihar tasks are complete. See `docs/contributors/harihar-api.md` for the operator JSON format and trusted Python `app.state.workflow_service.registry_adapter.execution_assignments(workflow, auth)` boundary. It returns currently revalidated exact grants without exposing references in HTTP UI responses. Approved canonical agent references carry server-issued allowed tool IDs; new edited revisions clear grants.

Review these inputs and the existing run/event/approval DTOs before implementing or enabling runtime consumption. Runtime must check approved workflow/version, trusted subject/workspace, scopes, every tool binding, budgets, destination resolution and current quota/policy/approval evidence; references are process-local. No connector or live approval service was implemented by Harihar. External-write approval evidence, runtime execution/history and global collection agreement remain your/shared-owner dependencies. Harihar tasks 3.2/3.3 require your services and 4.4 requires your actual review; no acceptance is invented.

Verification recorded by Harihar: 50 Python tests, 61 frontend tests, 8 production browser scenarios, build/types/lint, canonical contract checks and strict OpenSpec all PASS. Tests make no provider/connector calls. This is a repository handoff update only; no external message was sent.

## Rethika consumer acceptance — 2026-10-10

Rethika explicitly accepted Aravind's delivered registry boundary and Harihar's delivered UI/API execution boundary in the contributor session, including process-local authorization and local-development limitations, and authorized Rethika implementation. Fresh verification: 50 Python planner/registry/API tests PASS using `.venv-integrations/bin/python`; shared contracts PASS; all 16 strict OpenSpec checks PASS. Acceptance covers delivered inputs, not unfinished runtime integration, production authentication, live connectors, or new lifecycle/trigger contracts. No external notification was sent.

## Core runtime implementation review — 2026-10-10

Fresh verification: 94 Python tests PASS (50 upstream, 44 runtime); 61 frontend
consumer/domain tests PASS; frontend TypeScript PASS; shared schemas/fixtures PASS;
generated-client drift check PASS; strict Rethika OpenSpec validation PASS with
zero issues; runtime dependency check PASS. No real model/email/trigger/provider
trace export was made by this verification. CrewAI import warnings are nonfatal.

The suite includes actual CrewAI dry-run and offline kickoff, actual OTel SDK spans,
exact registry-issued tool binding/approval/revocation scenarios, no-tool-before-gate,
rejection/timeout stop/branch/retry, deterministic branch/join and error-path isolation,
cumulative workflow/agent budgets, explicit model request bounds, duplicate/restart
run identity, tool isolation, unknown invocation recovery, safe SMTP transport,
secret-bearing result rejection, worker identity resolution and HTTP consumers.

Reviewable offline evidence: `.local/runtime-review/evidence.json` and its
repository-local database contain completed run
`run_6d7724cd39494fb2b628863faf3eacf6`, five canonical events and five in-memory SDK
spans. This is explicitly a deterministic test fixture with test-only approval
provenance, not real workflow release/connector acceptance.

Inputs: exact approved ID/version/document with workspace/validation/review
provenance; current trusted execution identity; currently authorized exact registry
assignments; explicit server model pricing/adapter and credential-reference resolver;
workflow inputs/request ID/retry key. Worker authentication must be freshly resolved.
Authorization/credential references are never UI response fields.

Transitions: queued → running; running → paused_for_approval/completed/failed/blocked/
cancelled; paused_for_approval → running/rejected/failed/blocked/cancelled. Terminal
states do not resurrect. Draft edits do not change old approved documents; a newer
approved revision supersedes manual execution. Release-specific immutable cutover
semantics remain new-contract work and are not claimed here.

Connector behavior: exact agent binding and current metadata, schema, scopes, policy,
approvals, destination and duration checks before invocation; committed intent before
external call; no automatic SMTP resend after uncertain submission. Stable Message-ID
is reconciliation data only. No live quota reservation/restart approval service exists.

Trace fields: event/run/workflow/version IDs, timestamp/source/type, safe node/outcome/
status/approval/error codes, correlation ID and application trace reference. No prompt,
credential, raw provider result or input payload is exported. Export is at least once
on delivery/checkpoint crash; consumers can deduplicate by event_id.

Remaining blockers: joint review of the concrete lifecycle/trigger contract proposal,
restart-safe authorization/approval reconstruction, incoming provider adapters, durable
release/event/jobs, overview streams and UI lifecycle actions, extended scenarios and
an explicitly approved real event-source demonstration. Existing external-write
publication approval integration also remains closed. Final task 4.4 and sections
5–8 acceptance stay open; this core review does not declare the segment ready.

Repository notification: Suprajha should review executable expression/input mappings;
Aravind should review trigger scopes/restart authorization; Harihar should review
lifecycle DTO/overview/stream integration; cross-segment POC/operations should consume
the run/trace limits and evidence. No external message was sent.

## Extended lifecycle acceptance — 2026-10-10

The four-owner unanimous review supersedes the historical blockers in the core review
above. `shared/contracts/workflow-operations-v2.json` is the additive authority for
immutable releases, triggers, automation identities, lifecycle operations, overview
records and resume events. Existing v1 operation names and state contracts were not
changed. The accepted transport and permission mapping is recorded in
`openspec/changes/rethika-runtime-observability/contract-review.md`.

Implemented behavior includes atomic first publish/republish with compensation and
optimistic conflict checks; trusted Registry reconstruction and fresh assignment
revalidation after restart; verified push events; polling baselines and transactional
checkpoints; timezone-aware schedule ticks; receipts, deduplicated jobs, leases,
bounded retries, dead letters and replay; release-pinned automation identities;
sequence-resumable authenticated SSE with snapshot/poll fallback; and overview Run,
Edit, Publish/Republish, Disable and confirmed Delete actions. Deletion tombstones the
workflow, blocks dispatch, cancels queued jobs and safe active runs, prevents approval
resume, retains audit data, and retries provider cleanup.

Exact incoming-provider inventory: `generic_hmac_webhook` is supported through the
real authenticated HTTP route with an opaque server secret reference, HMAC-SHA256 and
five-minute freshness. `fake_push`, `fake_poll`, and `fake_schedule` are test adapters.
SMTP is outbound only. GitHub, Google, Gmail/IMAP, Slack, and arbitrary Registry tools
are not claimed as event sources. No external provider account or network side effect
was used in acceptance.

Fresh evidence: 102 Python tests passed, including eight lifecycle suites and signed
HTTP delivery; 62 frontend tests passed; eight Playwright browser flows passed;
frontend typecheck, lint and production build passed; shared-contract validation,
generated-client drift, `pip check`, and strict OpenSpec validation passed. The local
replay artifact is `.local/lifecycle-review/evidence.json` and records release
`rel_44cffa4d2f64441eaef4b038ae408c07`, receipt
`receipt_6654ac99af1f478db705c27a8bfea6f1`, job
`job_1fd96994865447028edda28d7e88840a`, run
`run_a38e3b8c92a64235a1e4f26ea231878b`, correlation
`corr_29e9af82fe5f46dc92bcc5f7c636c45d`, and trace
`trace_0f0437cc5a1549b2a44e6666602c4a04`, with five canonical run events and overview
sequences 1–3. This is deterministic local evidence, not a claim of external delivery.

## Cross-segment vertical slice implementation — 2026-10-10

The companion `cross-segment-poc-integration` change now implements the planner-to-Registry
bridge rather than only verifying it. Planned agents receive workflow-scoped IDs; the
trusted adapter registers normalized agent definitions, resolves capabilities to enabled
schema-compatible tools, preserves unresolved requirements, and materializes explicit tool
nodes with typed mappings. Revision approval installs Registry evidence through the
configured operator permission and approver role; runtime approval hashes the exact action
boundary before an external connector call. The browser fixture includes controlled SMTP
metadata and deterministic offline CrewAI, Sheets, and SMTP adapters; it never sends a real
message.

Evidence: 105 Python tests, 62 frontend tests, frontend typecheck/lint/build, shared
contract validation, strict cross-segment OpenSpec validation, and `git diff --check` pass.
The controlled vertical slice plans an email workflow, resolves `smtp_send_email`, publishes
it, pauses at run approval, resumes after an `approver` decision, and completes through the
offline connector. Real SMTP delivery and final four-owner acceptance remain explicitly
unclaimed until operator credentials and human signoff are provided.

## Slack Socket Mode / Gmail implementation — 2026-10-10

The scoped `slack-gmail-socket-mode` change adds a product Socket Mode receiver, operator Gmail Registry bootstrap, real SMTP connector, release/dispatch/runtime workers, hidden app-token entry, and deterministic mapped draft setup. Existing drafts and shared contracts are preserved. Release execution now strips lifecycle-only context at canonical auth boundaries, retains exact publisher-bound grants and resumes automation approvals through fresh worker identity. Approvals/Runs use the server run collection so concurrent DM notification requests are visible.

Verification: 126 Python tests (10 new Slack/Gmail scenarios), 63 frontend tests, typecheck, lint, production build, shared contracts/generated-client drift and strict OpenSpec PASS. Gmail STARTTLS/AUTH/NOOP was verified with saved credentials; no email was submitted. Live Slack event/mail acceptance remains pending the operator's app-level token and team/DM/member IDs. Setup instructions: `docs/slack-gmail.md`. Email sends retain the existing per-action approval boundary; no automatic approval or contributor acceptance is claimed.

Focused browser checks: both approve and reject scenarios passed using `cd frontend && npm run test:e2e -- --config playwright.slack-gmail.config.ts`. These checks mock the API; the Python integration tests separately verify actual application lifecycle and SMTP connector logic with an offline transport.

The broader legacy browser suite was also attempted on isolated ports: 1/8 passed, 7 failed against builder controls/labels such as Create draft, Save revision and Registry review. These failures are recorded in `.local/slack-gmail-browser-tests.log` and are not counted as passing integration evidence. No builder redesign or unrelated selector rewrite was included.

## Workflow-owned live providers — 2026-10-10

`scripts/run_live_backend.py` supplies reusable Google Sheets, bounded OpenAI/CrewAI and Gmail adapters plus durable workers. It creates no business workflow. The UI-authored canonical workflow owns source range, row identity, conditions, agent handoffs, email content and approvals. Fixed persisted binding-to-release lookup, stable row.created polling, incomplete-row handling, filtered/duplicate batch checkpoints, source health recovery and authored output mappings. Polling source grants no longer append a second Sheets read after an action. Gmail retains action approval and no automatic retry after uncertain submission.

Evidence: 135 Python tests passed; the final scheduler/lifecycle focused rerun passed 18 tests. 63 frontend tests, typecheck, lint, production build, canonical contracts/client drift, dependency consistency and strict scoped OpenSpec validation passed. Both focused approval browser scenarios passed with a mocked API. Earlier broad legacy browser failures remain unclaimed.

Live checks verified the selected Sheet, Gmail STARTTLS/AUTH/NOOP and model availability. A synthetic model-generated draft passed validation and Registry revision approval, then a synthetic row triggered two actual CrewAI/model steps and paused for human action approval. No email was submitted. Logs: `.local/synthetic-runtime-check.log`, `.local/live-provider-tests.log`, `.local/live-provider-browser-tests.log`. Automatic approval review rejected sending the real Sheet configuration to the live planner; synthetic data was used instead. Real delivery requires UI publication, a new row after baseline and action approval. Setup: `docs/sheets-gmail.md`. No contributor acceptance is inferred.

## Live source recovery — 2026-10-10

The user's published source had a full Google Sheets URL in resource_id, causing SHEETS_READ_FAILED and no baseline/jobs/runs. The provider boundary now extracts the ID from an HTTPS docs.google.com Sheet URL and rejects foreign URLs. No published workflow was rewritten or recreated. A second failure came from the existing database's legacy checkpoint key: composite ON CONFLICT failed after the initial baseline. Workspace-scoped UPDATE/INSERT checkpoint persistence now supports the legacy and current tables without resetting data.

The live backend was restarted with both fixes. The actual published source reports health=ready with no error; its existing baseline contains four identities and subsequent checkpoint updates succeed. UI session/runs endpoints return 200. Rows added before the successful baseline intentionally create no runs; the user must refresh the browser and append a new unique High-priority row. No email was sent and no approval was bypassed. Verification: 138 Python tests, including URL-backed dispatch and legacy checkpoint recovery; contracts, generated-client drift and strict OpenSpec validation passed. Logs: .local/sheet-url-all-tests.log and .local/live-backend-recovery.log.

## Explicit direct-send mode and wrong-service diagnosis — 2026-10-10

The user's new screenshot was traced to an unrelated service on port 8000: the frontend proxy received HTTP 404 JSON with only a detail field for session/workflows/runs. The managed Builder backend was already absent; the unrelated service was left untouched. No Builder backend is left running. Updated commands use port 8002 and an explicit frontend BUILDER_API_URL; the proxy now reports canonical API_WRONG_SERVICE when upstream JSON lacks a Builder envelope.

At the user's explicit request, BUILDER_EMAIL_DIRECT_SEND=1 permits the configured smtp_send_email tool to send from an approved published workflow without a per-action gate. Registry approval_required=false, the graph runner's server-owned direct tool allowlist and SMTP connector opt-in must all agree; exact grants, credentials, recipient/host restrictions, schema guardrails, budgets, dedup and uncertain-send no-retry remain enforced. Default approval behavior and workflows retaining approval nodes remain unchanged. The user will regenerate/edit and publish the workflow; no stored published revision was rewritten.

Evidence: 141 Python tests and 65 frontend tests pass, along with typecheck, lint, canonical contracts/client drift, strict scoped OpenSpec and diff checks. Direct-send tests run two CrewAI agents and exactly one offline SMTP submission, skip Low rows and deny direct grants without runner/connector opt-in. No live email was submitted. Updated objective and commands: docs/sheets-gmail.md.

## Interactive node traces — 2026-10-11

Added bounded, redacted observations, actual outputs, evaluated condition evidence, successor paths and node failure attribution to existing canonical run-event details. Mesh editor selects real runs, polls events, highlights statuses/paths and opens Trace or Configuration on node click. Historical snapshots are not invented. Private reasoning fields and credentials are redacted; payloads remain excluded from telemetry export. All 157 backend tests, 71 frontend tests, types/lint/build/contracts/strict scoped OpenSpec pass; desktop/mobile run-switching browser checks and read-only live refund workflow smoke check pass. The idle configured backend on 8002 was gracefully restarted with its original arguments/environment; editor remains on 3001. No manual provider invocation, workflow execution or email send occurred in verification.

Live trace acceptance check: clicked all 7 nodes across both historical runs, switched runs, opened Configuration and tested mobile; no browser errors. Executed a synthetic Closed/Refund ticket TRACE-TEST-IGNORED through the actual published workflow as run_07facbe0682f40fb8d66683d34568965. Run completed with recorded observation, exact expression, false/no outcome, selected ignored edge and output. All model/email nodes skipped; browser verified the fresh trace and two highlighted executed edges. Historical wording corrected to avoid claiming unavailable output/successor evidence. Types/lint and all 71 frontend tests pass. Fresh AI/email branch was not executed in this acceptance check.

## Agent communication diagram — 2026-10-11

Added an interactive read-only UUID diagram beside node traces. Canonical parent_agent_id/hierarchy_role and local draft relationships drive master/sub-agent labels; configured parent edges stay distinct from recorded graph transitions/data mappings. Exact run revisions load independently of the current draft. UUIDv5 node IDs remain stable without document writes; runtime handoffs/invocations use UUIDv4 with redacted bounded input/output evidence, data/control distinctions and per-attempt final result/timing correlation. No execution grants, shared schema shape, provider dispatch semantics or unsupported local hierarchy behavior changed.

Verification: full 161 Python tests, final 51 runtime tests, 77 frontend tests, types/lint/production build/contracts/strict scoped OpenSpec and all four desktop/mobile trace/communication scenarios pass. Tests verify registered offline master/sub-agent task exchange, actual received inputs and returned result, dynamic reference disclosure, retry UUIDs, cross-run/revision isolation, UUID stability, polling and historical graph switching. No existing canonical hierarchy workflow was found in the live collection; browser hierarchy fixtures and the offline registered runtime test cover that case. The idle live backend was restarted with its original configuration. Fresh Closed-ticket run run_090bd683558a44928495f6f7687f6055 completed with two correlated handoff UUIDs, and desktop/mobile live diagram inspection passed with no browser errors. Model/email steps stayed skipped. Screenshots: .local/agent-communication-desktop.png, .local/agent-communication-mobile.png, .local/agent-communication-live.png.
## Dynamic runtime delegation — 2026-10-11

The user rejected static hierarchy-only execution and explicitly requested workflow-independent dynamic delegation. The additive `dynamic-delegation-v1.json` validates optional metadata; existing v1 schemas remain unchanged. Hierarchy generation now creates a registered specialist pool and one dynamic master. Bounded model decisions choose task inputs and specialists at runtime, consume results and can spawn follow-up instances or finish. The application persists intents, invocation/task/handoff UUIDs, observations, concise reasons, child outcomes and return transfers; validates full batches and exact revision/Registry bindings; enforces approvals, cumulative budgets and task/round ceilings; stops on cancellation and blocks interrupted-parent recovery without replaying partial work. Per-call model limits narrow registered authority. Tools stay on authorized graph paths; batches run sequentially and nested autonomous spawning/new unregistered identities are not supported.

The run diagram adds exact-run spawned nodes during polling, fits newly added nodes and exposes task/result arrows on separate paths. Configured view shows available specialists. Dynamic generation has a separate identity from older static documents for the same objective. Existing published workflows were preserved.

Verification: 173 Python tests, 78 frontend tests, production build/types, lint, contract fixtures, strict scoped OpenSpec and six desktop/mobile browser checks passed. Real bounded CrewAI runs with offline transport verify dynamic choices, repeated spawning, budget/approval denial, no partial-batch retry and cancellation/recovery. Live configured-model workflow `planned_02488ce39981ef9d` was saved/validated/approved through the normal API without tools or event triggers. Classification run `run_4de7723ea0554429b82f08887cfb7360` spawned the classification specialist; summary run `run_93e3b0565a114b558c941b54489a4ad2` spawned the summary-writing specialist. Both completed with delegate/finish decisions, received results and no errors. Actual live desktop/mobile inspection passed for both runs with zero browser errors. Evidence: `.local/live-dynamic-delegation-evidence.json` and `.local/live-dynamic-desktop-run_93e3b0565a114b558c941b54489a4ad2.png`. Managed backend 8002 was gracefully reloaded with its original configuration after checking it was idle; unrelated services were untouched. No email or external-action tool was invoked by acceptance.

## Multiple dynamic task instances — 2026-10-11

Live scenario `run_c3df77212a2344d986c2c3da087fed02` asked the master to classify two fictional tickets independently, then summarize both results. The master made three decision turns, spawned two instances of the classification specialist and one summary specialist, and completed successfully. All three invocation UUIDs and six send/return handoff UUIDs were unique and correctly correlated. No external-action tools were called.

Browser acceptance exposed a real Dagre layout failure with several return edges to the same master. Placement now deduplicates forward dependency constraints and excludes result cycles while rendering all actual bidirectional handoffs. Dynamic task handoffs replace redundant parent lines; separate bottom/top return handles and curved return paths prevent crossing child cards. Initial view uses the selected run ID even while trace data loads. The exact live event fixture is retained in `frontend/e2e/fixtures/multitask-delegation.json` for regression coverage.

Verification: all 79 frontend tests, production build/type checks, lint and eight desktop/mobile browser scenarios pass. The live backend-connected browser opened each of the three instances and all six handoffs on both viewports with zero console/page errors; desktop edge labels have no overlaps. Screenshots and reports: `.local/multitask-uuid-desktop.png`, `.local/multitask-uuid-mobile.png`, `.local/multitask-browser-report.json`, `.local/multitask-delegation-evidence.json`. Mobile exposes the same UUIDs/traces through an accessible agent/link list. This verifies the bounded registered-specialist scenario; it does not introduce nested autonomous spawning or arbitrary agent creation.

## Prompt-only workflow setup — 2026-10-11

New Overview requests use one process prompt and opt into automatic input handling. The live planner saves known settings in existing node constants, fetches fresh facts through authorized tools, and maps changing event data from trigger templates. Automatic validation rejects manual fields, unmapped optional fields and undeclared input references. Planner identity distinguishes automatic proposals from prior saved workflows. No shared v1 contract or existing published revision was rewritten.

Run published loads the exact published revision. Automatic manual workflows submit empty inputs; automatic event workflows explain that their configured source starts execution. Legacy manual workflows retain their input flow. Setup examples: `docs/prompt-only-automation.md`.

Verification: 197 backend tests, 80 frontend tests, types/lint/production build, contracts and strict scoped OpenSpec pass. Six desktop/mobile browser scenarios verify single-prompt creation, empty-input execution, event guidance, published-version isolation and no dialogs. Backend tests cover bounded planner correction, actual Sheets adapter execution with saved constants and offline transports, and published automatic event polling with no user inputs. The configured live model produced a valid three-node dynamic workflow with inputs=[] and no unresolved requirements; synthetic resource only, no publication or execution. Evidence: `.local/prompt-only-live-proposal.json`, `.local/prompt-only-browser-tests.log`. The idle Builder backend on 8002 was reloaded with its original configuration. The actual UI on 3001 shows one prompt and a successful backend session with no browser errors; screenshot `.local/prompt-only-live-ui.png`. No email was sent.

## Local session recovery — 2026-10-11

Backend restarts rotate the development session cookie. Previously open workflow pages polled with the expired cookie indefinitely and retained their authentication banner. WorkflowClient now renews a validated local-development session after an explicit canonical HTTP 401 AUTHENTICATION_REQUIRED response, shares concurrent renewals, handles late stale responses and retries each rejected request once. Original action bodies and idempotency keys remain exact. Session endpoint failures, repeated rejection, non-local modes and authorization denials do not loop. Successful overview polling clears only an old authentication error.

Verification: 87 frontend tests, production build, types/lint, contracts, scoped strict OpenSpec and two desktop/mobile recovery browser scenarios pass. Read-only checks against the running UI/backend deliberately replaced isolated browser cookies, observed real 401 rejection, successful session renewal and fresh overview polling without reload. Both viewports had zero authentication banners and page errors afterward. Evidence: `.local/session-recovery-live.json`, `.local/session-recovery-live-desktop.png`, `.local/session-recovery-live-mobile.png`, `.local/session-recovery-browser-tests.log`. No backend restart, workflow execution, source changes or email sends were performed for this fix.

Generation availability follow-up: the backend and frontend proxy both reported planning_available=true with workflow.plan permission. The Overview's old cached-session guard displayed the same unavailable message for missing sessions, denied permissions and disabled planning. Generate now awaits session initialization and reads the current store before checking authorization and availability; connection, permission and disabled-planner failures have distinct messages. All 87 frontend tests, build/types/lint, strict scoped OpenSpec and eight desktop/mobile prompt/recovery scenarios pass. The prompt-only setup checks begin with stale availability and missing planner permission, then verify that refreshed authority permits generation. A running-UI check used real session/collection endpoints and intercepted plan/save to avoid creating workflows; it observed two session reads, one planning request and no page errors. Logs: `.local/planner-session-browser-tests.log`, `.local/planner-session-build.log`.

## Regeneration after deletion — 2026-10-12

The user's inventory workflow had been deleted but its published revision remained as history. The same prompt produced the same planner ID; initial-save conflict recovery reopened that retained published revision, and the UI's approved-status guard reported a misleading review requirement despite empty unresolved requirements. The authenticated planning boundary now follows workspace-local deletion records to allocate a stable replacement ID, copies cached planner responses and rebinds agent, parent and node references before returning a fresh proposal. Further deletion yields a new replacement; existing replacements remain stable. Historical revisions, tombstones and approvals are preserved.

Verification: all 199 backend tests, shared contracts, strict scoped OpenSpec and diff checks pass. New HTTP/API tests verify same-key retries, fresh draft saving, agent isolation, successive deletions and unchanged historical data; another test verifies workspace isolation. A read-only check of the actual deleted inventory revision resolved its replacement identity while confirming history was unchanged. The idle backend on 8002 was reloaded with its existing configuration. No new live workflow was saved, published, executed or restored by verification. Evidence: `.local/recreate-workflow-tests.log`, `.local/recreate-workflow-all-tests.log`, `.local/recreate-workflow-backend.log`.


## Data Intelligence Phase 5 — 2026-10-17

Delivered bounded federated PostgreSQL fact aggregation with PostgreSQL/MongoDB dimensions, complete pre-filter join checks, exact weighted aggregate merging, native average finalization and per-fragment UI evidence. Data-query contracts add the federated strategy and optional execution fragments; workflow/agent/tool contracts are unchanged. Existing ownership, management/read permissions, expiry, freshness, no-result-history and source review rules remain. Unsupported shapes retain bounded fallback; separate databases have no atomic shared snapshot. See `docs/cloud-federation-phase5.md` for exact support and limits.

Verification: 137 backend tests, 68 focused frontend/domain tests, four desktop/mobile browser fixture scenarios, types/lint/production build/contracts/strict OpenSpec passed. Deployed public real-model acceptance matched all eight cross-source category sales totals and weighted averages against independent SQL/category reads, with 2,155 fact rows and two strict joins. Live native average over 77 products also matched. Backend/frontend/worker active; no cloud data, credentials or review decisions changed. This records delivery evidence, not contributor acceptance or external notification.


## Data Intelligence Phase 6 — 2026-10-18

Delivered owned durable query jobs, shared-store claims, attempt/lease fencing, current-authority checks, progress, cancellation, one fresh recovery attempt and encrypted results retained for 15 minutes. Job/plan metadata lasts up to 24 hours. The Questions UI restores jobs after refresh, clears expired rows and preserves submission keys across uncertain responses. The production proxy forwards the exact query-job idempotency header. Worker supervision includes DataQueryJobs; API-only mode does not consume jobs. Existing synchronous execution remains compatible with its prior bound.

Data-query contracts add query-jobs-v1 and optional status/canonical envelope metadata; workflow/agent/tool contracts are unchanged. Default absolute job budget is 180 s from submission (configurable 45–300), also bounded by plan expiry; existing source/statement/precision/transfer budgets remain. This deployment retains its server-configured development identity, not newly implemented production IAM. See `docs/cloud-query-jobs-phase6.md` for exact behavior and limitations.

Verification: 178 backend tests, 103 focused frontend/domain/proxy tests, ten desktop/mobile browser fixture checks, types/lint/build/contracts/strict OpenSpec pass. Isolated tests cover real PostgreSQL cancellation, killed-worker recovery, PostgreSQL-store competing claims, cancellation/publication races and encrypted expiry. Live public federation matched eight independent category sales sums/weighted averages across 2,155 order details; the same job/result survived API restart/browser refresh. A second live active job cancelled without result rows. Services active. No connected cloud rows, credentials or relationship review decisions changed; job/plan/audit writes were normal authorized query metadata. This records evidence, not contributor acceptance or external notification.


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

## Semantic Knowledge graph — 18 October 2026

Status: ready-for-handoff for deployed UI, metadata retrieval, semantic review and bounded actual-record execution. Live model activation remains blocked pending explicit schema/destination authorization; no downstream acceptance is implied.

One Knowledge graph replaces the separate map/detailed navigation. Structured semantic proposals retain original technical provenance; ambiguity/review and technical join permission stay separate. Actual-record mode uses validated read plans and observed key matches. Workflow source selection consumes semantic context and pins its evidence basis. Metadata changes invalidate affected meanings/workflows.

Verified build s3UuI6ax0MMm4xtwwg4RX is live, all three services healthy, previous static assets retained and credential/write-policy hashes unchanged. Offline/native/HTTP/UI tests and desktop/mobile browser checks passed; exact overlapping test counts and limits are in openspec/changes/semantic-knowledge-graph/verification.md. No cloud writes, Google actions or live model extraction were executed. Extraction is default-off at both job and provider boundaries after automatic approval review rejected schema transfer without destination-specific authorization. Next: owner UI acceptance and explicit schema-only authorization before enabling extraction to the configured OpenAI destination. See docs/semantic-knowledge-graph.md.

### Semantic extraction activation update — 18 October 2026

The owner explicitly authorized automatic schema-only extraction to api.openai.com
using gpt-5.6-luna. Enabled the existing flag and gracefully restarted API/worker;
all services healthy. Initial live inference is ready: 10 relationships, 6
inferred with validated evidence and 4 ambiguous. Previous authorization block
is resolved for this exact payload/destination. Labels remain inferred pending
business review. No record payload, external email/Calendar action, database write
or credential/write-policy change was introduced. Evidence:
.local/semantic-kg/inference-result.json and enable-inference.log.


## Reliable inventory report — 18 October 2026

Delivered a bounded fresh-prompt compiler using owned KG candidates and exact accepted/declared source links, deterministic stock/on-order ranking with honest watchlist labels, verified new-Sheet URL delivery and separate spreadsheet/email/calendar action gates. Registry validation and scoped connector execution enforce immediate approval evidence independently of legacy procurement automatic settings. An owner-scoped Google default reuses the user's previously selected account; explicit choices still override it. Existing frontend, credentials and database write policy are unchanged.

Verification: 183 backend/connector tests and 10 subtests passed; contracts, syntax and strict OpenSpec passed. Changes activated; Atlas/Supabase, public research and selected Google identity/capabilities verified. No live workflow was created or executed and no Google artifact was created. User performs the UI acceptance test. See docs/reliable-inventory-report.md and openspec/changes/reliable-inventory-report/verification.md for boundaries/evidence. This is a repository handoff, not an external notification or inferred contributor acceptance.


## Manual worker assignment recovery — 18 October 2026

Fixed fresh manual workers losing process-local tool approval evidence after API publication. Recovery requires the same currently authorized approver, exact workspace and validated published revision; current Registry scopes/policy and action approvals remain enforced. Fresh-service safety regression passed; 90 overlapping tests and 29 subtests passed. One unrelated empty-tool-list expectation fails unchanged against the original implementation. Real published revision preflight authorized all ten tools without running any workflow or external action. See openspec/changes/manual-worker-authorization/verification.md and its activation evidence. Existing terminal blocked runs require a new manual run; no draft rewrite or republish is needed.


## Typed research control messages — 18 October 2026

Published v1 inventory run read/normalized real inventory, then its research child failed MODEL_OUTPUT_SCHEMA_INVALID before tool execution. Raw response is unavailable; no specific invalid field is asserted. Closed registered tool inputs and closed business outputs now use direct typed response-schema fields instead of fragile JSON-in-string transport; generic/open schemas retain fallback. Registry and per-action gates remain unchanged. 55 protocol/delegation/report regressions and 3 subtests passed, including offline real CrewAI/provider bridge. Contracts/strict OpenSpec passed. Local published-v1 schema preflight passed without a model or connector call. Backend/worker activation evidence is under .local/research-control-fix. No user run or cloud write was executed. See openspec/changes/typed-agent-control/verification.md for the blocked live diagnostic, verification limits and separate draft-v2 registry banner.


## Single-decision provider response — 18 October 2026

User-authorized live read-only diagnostics reproduced the missing cause of the research failure: SDK output_text sometimes concatenates several complete control envelopes, which single-document parsing rejects. The control decoder now validates the entire bounded stream and consumes only its first decision; no later speculative tool action/finish is executed. Non-control JSON, Registry gates, action approvals and usage limits remain intact. 48 regressions and 7 subtests passed; live tool and finish diagnostics passed with synthetic public inputs, and contracts/strict OpenSpec passed. Backend/worker deployment leaves frontend/config and workflow definitions unchanged. No user run or Google action was executed. See openspec/changes/single-decision-response/verification.md and .local/research-control-diagnostic/activation.json.
