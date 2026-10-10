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
