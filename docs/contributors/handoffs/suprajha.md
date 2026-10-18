# Handoff — Suprajha

## Planner condition fix — 2026-10-10

The UI reported `WORKFLOW_VALIDATION_FAILED` at `conditions.expression` while planning an incoming Slack sender-filter/email workflow. The production provider prompt omitted the deterministic runtime grammar. Added grammar/examples and unknown-identity instructions; fresh canonical yes/no proposals with unsupported expressions now retain their branches, declare a required boolean review input, and record an unresolved `condition_mapping_required` requirement instead of guessing the expression. Saved/approved workflow validation is unchanged and still rejects unsupported syntax or missing branch paths. Non-boolean mappings are not repaired. Registry review retains unresolved condition mapping as a publication blocker.

Files: `planner/provider.py`, `planner/service.py`, `planner/validation.py`, `tests/test_planner.py`, and the generic-execution design note. Verification: all 115 Python tests PASS, including 22 planner tests; shared schemas/fixtures PASS; strict generic-tool-workflow-execution OpenSpec validation PASS. No live model or connector calls were made for this fix. The UI is unchanged. Restart the backend to load the updated planner. Incoming Slack automation still requires configured Slack Events authorization and exact sender/event mappings; outbound webhook delivery is not incoming-event access.

- **Segment:** Natural-language planning pipeline
- **Status:** accepted (Aravind acceptance recorded 2026-10-09)
- **Contract versions:** workflow-schema-v1, agent-contract-v1, tool-contract-v1, api-payloads-v1, error-format-v1, auth-permissions-v1, branching-approvals-v1, run-status-versioning-v1
- **Completed work:** Tasks 1.1–4.3 are complete (13/14 tracked tasks). This includes the planner request boundary, canonical contract loading, workspace-scoped idempotency, replaceable OpenAI structured-output adapter, OpenAI as the production default, deterministic provider for tests only, generic objective decomposition, capability/tool-reference extraction, conditional branches, approval/rejection paths, graph validation, secret rejection, safe error mapping, contract tests, environment configuration, and downstream handoff documentation. Task 4.4 local acceptance evidence is complete; Aravind has now accepted the handoff; Suprajha should synchronize task 4.4 with this recorded acceptance.
- **Files changed:** `planner/__init__.py`, `planner/contracts.py`, `planner/errors.py`, `planner/auth.py`, `planner/idempotency.py`, `planner/provider.py`, `planner/validation.py`, `planner/service.py`, `tests/test_planner.py`, `requirements.txt`, `.env.example`, `.gitignore`, `openspec/changes/suprajha-planning-pipeline/tasks.md`, and this handoff file. Local `.env` contains the operator-provided key and is ignored; its value is not part of the handoff.
- **Validation evidence:** `python3 -m unittest discover -s tests -v` — 14 tests passed; `python3 scripts/validate_contracts.py` — schemas and fixtures valid; `openspec validate suprajha-planning-pipeline --type change --strict --json` — valid with zero issues; three generic acceptance flows (support, onboarding, procurement/reporting) returned status 200 and passed workflow-schema validation; live OpenAI integration check returned status 200 and a schema-valid 3-node workflow.
- **Known defects:** The default provider now uses OpenAI and requires a configured `OPENAI_API_KEY`; the deterministic provider is test-only. The in-memory idempotency store is process-local and is not a durable persistence layer. Tool assignment, permissions, credentials, and execution remain downstream responsibilities.
- **Unresolved decisions:** None for the planning pipeline contract boundary.
- **Dependencies:** Accepted v1 shared contracts; `jsonschema` and `openai` dependencies from `requirements.txt`; `OPENAI_API_KEY` and `OPENAI_MODEL` in the local `.env` for live planning. The planner must precede Aravind’s registry work.
- **Downstream notifications:** Aravind accepted the capability and unresolved-requirement contract on 2026-10-09. Harihar and Rethika are notified through their contributor handoff files. Suprajha should synchronize task 4.4 with the acceptance record.
- **Next actions:** Aravind has reviewed and accepted the capability identifiers and unresolved requirements below and may consume the planner response contract. Harihar can consume the `data.workflow` response for draft rendering; Rethika can consume only approved revisions and must not execute planner drafts directly.
- **Blockers:** None for the planner segment. Downstream registry, UI, and runtime implementation remains intentionally out of scope.

Acceptance review status: local planner tests, contract validation, strict OpenSpec validation, and three generic flows passed. Aravind’s downstream acceptance is recorded below; the upstream task 4.4 checkbox remains for Suprajha to synchronize.

## Exact instructions for the next contributor — Aravind

1. Review this handoff and run `python3 -m unittest discover -s tests -v` plus `python3 scripts/validate_contracts.py`.
2. Treat `workflow.agents[*].capabilities` as planner requirements only. Resolve them through the Tool Registry; do not grant permissions, scopes, credentials, or executable tools from planner output.
3. Consume `workflow.tools[*].capability` only when the tool identifier is accepted by the registry. Unknown operations are represented in `metadata.unresolved_requirements` and must remain unresolved until a registry entry exists.
4. Preserve `workflow_planner_agent.allowed_tool_ids` as empty until least-privilege assignment is performed. Do not fabricate tools for unresolved requirements.
5. Verify risky objectives retain `approval_gates`, explicit approved/rejected paths, and `execution_policy.requires_review_before_execution`.
6. Record your review decision and any defects in the Aravind handoff, then notify Harihar and Rethika. After acceptance, check task 4.4 only if all local evidence and the downstream review are recorded.

## Planner implementation handoff

The planner accepts a `plan_workflow` request with `request_id`, `idempotency_key`, and a payload containing `objective` plus `auth_context`. A successful response has status `200` and returns `data.workflow`, `data.correlation_id`, and `data.contract_versions`. A repeated idempotency key in the same workspace returns the original response; reusing it for a different fingerprint returns `IDEMPOTENCY_KEY_REUSED`.

Capability identifiers emitted by the planner include `classify_text`, `retrieve_records`, `generate_report`, `read_spreadsheet`, `send_email`, and `send_notification` when the objective requires them. Accepted tool references are limited to `google_sheets_read_rows` and `smtp_send_email`; unknown operations remain in `metadata.unresolved_requirements` and are never fabricated.

Planner agent requirements are emitted in `workflow.agents`: `workflow_planner_agent` requires the identified capabilities, has no assigned executable tools, and requests only `workflow.read_input`. Aravind must resolve capabilities and authorize tools; the planner never grants scopes or creates credentials.

Risky external actions set `execution_policy.allow_external_writes`, include an approval gate for the `approver` role, and expose explicit approved and rejected paths. Conditions expose declared `yes`/`no` outcomes. All drafts remain `draft` and require review before execution.

Downstream inputs:

- **Aravind:** `workflow.agents[*].capabilities`, `workflow.tools[*].capability`, `metadata.unresolved_requirements`; resolve assignments without inventing permissions.
- **Harihar:** `data.workflow`, `data.correlation_id`, `data.contract_versions`, and stable error fields for draft UI rendering.
- **Rethika:** draft/run boundary, approval metadata, execution policy, and error policy; accept only a later approved workflow revision with authorized assignments.

## Aravind acceptance — 2026-10-09

Aravind explicitly accepted this planner handoff in the contributor session. Local review reran all 14 planner tests and contract validation successfully; strict OpenSpec validation returned valid with zero issues. Capability identifiers, unresolved requirements, empty planner tool assignments, and approval metadata are accepted as registry inputs. Existing process-local idempotency and production credential requirements remain documented limitations. This records downstream acceptance, not new planner implementation.

## Rethika core runtime delivery — 2026-10-10

Rethika accepted the delivered upstream registry/UI/API boundaries and has delivered the core runtime through existing canonical operations. Fresh verification: 94 Python tests (50 upstream, 44 runtime), 61 frontend tests, TypeScript, contract/drift checks, runtime dependencies and strict OpenSpec PASS. Runtime routes remain disabled by default and can be explicitly connected; no live model/email/trigger demonstration or final segment acceptance is claimed. See `runtime/README.md` and `docs/contributors/handoffs/rethika.md` for server adapters, approval/worker/grant boundaries and remaining publication/production limits.

Joint review requested for `openspec/changes/rethika-runtime-observability/contract-review.md` and its companion draft schema before release/trigger/automation/overview implementation. Suprajha reviews executable input/expression mappings; Aravind reviews trigger scopes and restart authorization; Harihar reviews lifecycle transport, DTOs and overview streams. All extension signoffs remain pending; existing shared contracts are unchanged. This is a repository handoff notification, not an external message or fabricated owner acceptance.

## Workflow-owned live planning — 2026-10-10

The live launcher adds nonsecret server context for the exact runtime model, enabled tool/capability IDs, approved permissions and notification recipients. Planner guidance specifies metadata trigger templates, event inputs, node output handoffs and approval boundaries. It no longer fabricates condition_result=true for Sheets. Live planning performs at most two bounded requests, including one correction for unsupported permissions/capabilities/configuration or nonexistent node references. SDK retries and Responses storage are disabled. Business rules remain authored in the workflow.

A synthetic live draft and two actual model agent steps were verified. 135 Python tests and canonical validation pass, including bounded correction tests. See `docs/sheets-gmail.md` and Rethika's accumulated handoff for evidence and live-delivery limitations. No contributor acceptance is inferred.

Planner assignment fix: fresh provider proposals are checked for secrets before clearing agent allowed_tool_ids and removing tool configuration_reference. This prevents UNTRUSTED_ASSIGNMENT during UI draft saving; forged client saves still fail, and Registry review remains responsible for assignments. Verification: 144 offline Python tests, shared contract validation and strict live-workflow-providers OpenSpec validation pass. Regression tests cover generation-to-save, client forgery and secrets in discarded fields. Restart the operator-managed backend to load the change. No live email was sent or backend started/stopped for this fix.


## Generated metadata safety correction — 2026-10-10

Live planning now applies Registry's safety scan before returning model proposals, uses the existing one bounded correction with code-only feedback, and reports repeated rejected output as PLANNER_OUTPUT_UNSAFE rather than blaming user input. Provider guidance excludes reserved credential metadata fields. Incoming credential rejection and Registry authorization remain unchanged. The original UI error's exact generated field could not be recovered; this fixes the verified mismatch between planner value checks and Registry key/value checks.

Verification: 154 Python tests PASS, shared contracts valid, strict live-workflow-providers OpenSpec valid, git diff --check PASS. New regressions cover reserved authorization metadata correction, repeated unsafe output without return/cache, and input secret rejection without model calls. A live inventory planning/save check passed against an isolated database; no workflow was activated or email sent. Backend restart approval was declined, so the existing port-8002 process still needs the operator to restart it with the documented direct-send command. Existing frontend edits are unrelated and were preserved.


## Complaint missing-email diagnosis — 2026-10-11 IST

The published complaint workflow received matching rows but failed before its first model call: BUDGET_EXHAUSTED. Its two model agents each reserve $0.05; its workflow omitted max_estimated_cost_usd, which runtime correctly treats as zero. Live planner correction now checks total model-node cost ceilings and guidance requires an explicit workflow ceiling. 45 focused planner/live-provider tests and shared contracts PASS.

Using the local authenticated API, prepared complaint workflow planned_d1477ce2f38deb07 version 2 as a draft with a $0.10 overall ceiling and 300-second timeout; cleared executable references through the canonical editable-revision flow. It remains unpublished for user review. Version-1 releases and blocked runs were preserved. No model or email calls occurred during repair. The running backend needs an operator restart to load preventive planner code; saved version 2 itself can be reviewed/published without restart.


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

## Northwind research/Sheets planning blockers — 18 October 2026

Fixed registered-tool visibility in DB-backed planning: web search/page read and
Sheets creation/setup definitions are included; obsolete Google-only composition
instruction corrected. Verified 35 source/procurement tests and 27 planner/provider
tests plus 4 subtests. Backend-only change live, configuration/frontend unchanged.
Existing Northwind draft still describes email/30 minutes; latest user intent is
no email, primary calendar, 19 October 2026 15:00–16:00 IST (60 minutes).

Full replacement is NOT ready: two generation-only attempts rejected by normal
validation, first restricted mappings then SHEETS_TARGET_REQUIRED. No replacement
saved or external actions executed. New Sheets setup returns proposed targets, but
same-run report population lacks an approved handoff to the concrete-target writer.
Do not remove that guard or old unresolved requirements to make submission pass.
Next required work is scoped new-spreadsheet report export with explicit approval
and ownership. Evidence: openspec/changes/planner-research-sheet-tools/verification.md.

## New spreadsheet report capability — 18 October 2026

Implemented and activated `extension_sheets_create_report` for DB-backed workflows.
One approved create request includes bounded literal report tabs/rows and returns a
read-verified URL/count/digest. Existing fixed spreadsheet destination ceilings,
ownership markers, uncertain-result journal and immediate approval checks remain.
Native + extension registration use existing creation opt-in; no credential/config,
frontend or Praxi changes. Planner receives exact schema and NEW-report guidance.

Evidence: 48 connector tests (+6 subtests), 59 planner/provider/source tests
(+4 subtests), one targeted native registration/approval test, contracts and strict
OpenSpec pass. Initial 5 failures were corrected and affected suite rerun green.
Backend/worker live; configuration hashes and frontend process unchanged. No real
Sheets, email, Calendar or DB mutation executed. Live-provider execution still
requires normal owner approval; do not claim it already ran.

Latest explicit user answers supersede earlier no-email/one-hour assumptions:
recipient is the selected Google account's own inbox, obtained through the bound
Gmail profile; meeting is primary calendar, 19 Oct 2026 15:30–16:00 Asia/Kolkata.
First generation-only check failed OUTPUT_FIELD_NOT_DECLARED (no draft saved).
A correction with exact output schema feedback and the old draft's selected Google
binding is being verified. Final evidence: openspec/changes/new-spreadsheet-report/verification.md.

Final follow-up: new-report grid size now derives from approved rows; connector48,
native1, contracts and final planner27 (+4 subtests) rerun green. Saved a corrected
authored Northwind draft `planned_cde21033218f6110` v1 through normal PlannerService,
KG binder and API save/validation: three real scoped datasets, existing Google
binding preserved, zero unresolved requirements, no non-approval tool failures.
It remains unapproved/unpublished/unexecuted. This is an authored correction of a
captured proposal, NOT proof that earlier automatic generations succeeded. Final
report guidance addresses observed mapping/capability/handoff/rejection defects;
final automatic check outcome is in final-live-plan.log. See updated verification.

Final automatic job `plan_9ec9f0b2c4374a338badce3dc96a2e51` failed
PLANNER_PROVIDER_FAILED. Automatic regeneration remains an unresolved planner
issue; the explicitly authored saved draft is separately validated and reviewable.
Do not report full automatic prompt-to-workflow success or real Google execution.


## Reliable inventory report — 18 October 2026

Delivered a bounded fresh-prompt compiler using owned KG candidates and exact accepted/declared source links, deterministic stock/on-order ranking with honest watchlist labels, verified new-Sheet URL delivery and separate spreadsheet/email/calendar action gates. Registry validation and scoped connector execution enforce immediate approval evidence independently of legacy procurement automatic settings. An owner-scoped Google default reuses the user's previously selected account; explicit choices still override it. Existing frontend, credentials and database write policy are unchanged.

Verification: 183 backend/connector tests and 10 subtests passed; contracts, syntax and strict OpenSpec passed. Changes activated; Atlas/Supabase, public research and selected Google identity/capabilities verified. No live workflow was created or executed and no Google artifact was created. User performs the UI acceptance test. See docs/reliable-inventory-report.md and openspec/changes/reliable-inventory-report/verification.md for boundaries/evidence. This is a repository handoff, not an external notification or inferred contributor acceptance.
