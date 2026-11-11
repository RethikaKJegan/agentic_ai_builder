# Unified Overview automation — implementation and qualification

Recorded 10 November 2026. Final qualification and the explicitly authorized
production rollout are complete. See [deployment](deployment.md) for the serving
release, scoped flags, preservation evidence and rollback.

## Architecture integration

The existing Overview prompt in automatic mode submits a versioned internal
request through the existing durable planning queue. The backend uses the
configured OpenAI transport with bounded structured output to interpret intent.
Owner-scoped ontology retrieval and relevance-filtered query metadata are reused;
registered capabilities, permissions, bindings and source mappings are validated
independently of the model. Read-only routes exclude external write capabilities.
Disabled routing preserves the legacy Overview dispatch.

The existing action planner compiles the workflow, CrewAI performs the existing
content tasks, and Registry plus the durable graph runtime authorize execution.
The existing automation scheduler persists reviewed consent, schedules,
occurrences and receipts. No second planner, ontology, executor, scheduler or
user-facing page was introduced. Shared canonical contracts are unchanged.

Changes and reasons:

| Files | Reason |
| --- | --- |
| `workflow_api/overview_automation.py` | Structured interpretation, workspace feature gate, persisted preparation, schedule proposal, scoped consent and activation adapter. |
| `workflow_api/temporal_queries.py` | Versioned calendar windows and replacement of only two reviewed time-bound filter values. |
| `workflow_api/business_ontology_routes.py`, `workflow_api/main.py` | Existing transport dispatch and session-advertised routing availability. |
| `workflow_api/planning_jobs.py` | Existing queue handoff, cancellation protection, request consistency checks and typed business-input errors. |
| `workflow_api/action_plans.py` | Allowed-operation filtering, pinned reviewed query context and immutable Overview metadata; future-tenant package default correction. |
| `workflow_api/business_composition.py` | Include Overview control metadata in immutable composition verification. |
| `runtime/action_plans.py`, `workflow_api/automation.py` | Resolve approved date bounds from persisted scheduled occurrence time and revalidate exact recurring consent. |
| `workflow_api/data_query_pushdown.py` | Native MongoDB datetime filtering with complete-source type validation and existing limits. |
| `workflow_api/action_bindings.py` | Permit generated cells only at native Sheets update `values`; generated spreadsheet IDs and ranges remain forbidden. |
| `frontend/src/api/client.ts`, `frontend/src/api/overview-automation.ts` | Existing planning transport and typed result/activation adapters. |
| `frontend/src/screens/app.index.tsx` | Existing prompt dispatch, owner-scoped refresh recovery and terminal-versus-uncertain retry handling. |
| `frontend/src/features/investigations/OverviewAutomationReview.tsx` | Inline schedule/consent review, cancellation, status, pause/resume/cancel and generation polling. |
| `frontend/src/features/investigations/ConnectedPlan.tsx` | Reuse existing workflow approval controls; scheduled proposals cannot be accidentally run manually. |
| `.env.example` | Document disabled-by-default flag, workspace allowlist and operator-owned timezone. |
| Focused backend/frontend/browser tests and OpenSpec artifacts | Controlled qualification, compatibility evidence and release handoff. |

## Route evidence

Interpretations in these tests are controlled structured responses, not paid
live-model classifications. Prompt examples describe the tested intent families;
they do not certify live-model accuracy for every wording.

| Prompt family | Intent and existing path | Actions and observed result |
| --- | --- | --- |
| Warranty-policy knowledge question | Knowledge → existing connected planning/retrieval | Read-only capability filtering; existing retrieval and planner regressions passed. No schedule or delivery authority. |
| Investigate complaint C123 and warranty evidence | Identified investigation → existing case readers | Fixed case evidence; finite whole-payload consent for repeated reader operations. Existing investigation regressions passed. |
| Operating-hours 0–100 population statistics; no external writes | Population → existing generic query/runtime | No ID requirement; trusted calculations, inclusive filters, evidence and coverage checked by population regressions. Proposed delivery is rejected. |
| Analyze mapped records once, create report and email an explicit recipient | One-time → existing query/CrewAI/graph | Waits for exact write approvals; actual fixture query, report and email adapters complete with receipts; no recurring schedule. |
| Daily report at 18:00 India time | Recurring → existing scheduler and graph | Reviewed cron `0 18 * * *`, timezone `Asia/Kolkata`, distinct occurrences, fresh reads and persisted receipts. Duplicate activation reuses one schedule. |
| Update the reviewed report and email its summary every day | Recurring → existing native Sheets update and Gmail adapters | Two controlled occurrences update only the pinned spreadsheet/range and send the reviewed summary. No real HTTP provider writes. |
| New complaint event / alert a manager | Event → capability limitation | No authorized complaint-created subscription exists in this integration; no imaginary trigger, recipient or manager is created. |
| Subway purchase-order and future-tenant requests | Existing tenant-scoped metadata/planner/package paths | Simpson/Subway discovery regressions and future-package default test passed. Missing mappings/destinations remain clarifications or validation failures. |
| Ambiguous request, malformed output or model timeout | Clarification / safe failure | No automation activation or external action. Confirmed failed jobs allow a new explicit retry; uncertain submissions retain the request identity. |

## Automation evidence

- Schedule conversion covers daily, weekdays, weekly, monthly and one-time dates through
  the existing cron validator. Missing timezone/hour requires clarification.
  One-time intent cannot become recurrence, and an overdue one-time proposal
  cannot silently roll into next year's matching cron date.
- Calendar windows cover today, yesterday, this/previous week, current/previous
  month and last 1–90 calendar days including the occurrence day. Week starts
  Monday. Ranges are half-open and converted from the reviewed timezone to UTC.
- Example: 10 November 2026 in Asia/Kolkata resolves to
  `[2026-11-09T18:30:00+00:00, 2026-11-10T18:30:00+00:00)`.
  A delayed occurrence crossing midnight retains its scheduled reporting day.
  A second occurrence resolves a new day; DST calendar-day behavior is tested.
- Consent pins the query, dataset, fields, filter structure, operations,
  destinations and limits. Only the two annotated date values may change.
  Runtime verifies the annotation against immutable workflow metadata.
- Controlled recurring graph: query → content preparation → report creation or
  native report update → email preparation → email send. Registered tools and
  existing content agents execute through Registry/CrewAI/graph services.
- Approval, revoked authority, overlap, missed-run policies, restart recovery,
  duplicate ticks and uncertain provider outcomes retain existing protections.
- Native report update requires a registered typed writer with zero retries,
  an explicitly reviewed spreadsheet and A1 range, and selected-account access.
  The controlled test verifies actual native connector invocation and persisted
  update/email receipts. Generated resource identity/range attempts are rejected.

## Verification commands and results

Commands ran from the repository root unless marked frontend. Counts are per
invocation and overlap; they must not be summed as distinct test cases.

| Command / log | Result |
| --- | --- |
| `.venv-integrations/bin/python -m pytest tests/test_overview_automation.py tests/test_overview_automation_api.py tests/test_overview_automation_integration.py tests/test_overview_planning_queue.py tests/test_mongo_temporal_queries.py tests/test_goal_planning.py tests/test_deleted_planning_retry.py -q --disable-warnings` — `/tmp/overview-resume-complete-backend.log` | 124 passed, 0 failed, 0 skipped. This run preceded the final narrow report-cell binding extension. |
| `.venv-integrations/bin/python -m pytest tests/test_connected_action_plans.py tests/test_intent_query_discovery.py tests/test_workflow_query_integration.py tests/test_workflow_population_acceptance.py tests/test_automatic_inputs.py tests/test_durable_automation.py tests/test_customer_automation.py tests/test_overview_contention.py tests/test_data_query_pushdown.py tests/test_workflow_query_clarification.py tests/test_query_envelope_bindings.py -q --disable-warnings` — `/tmp/overview-resume-regression.log` | 151 passed, 21 PostgreSQL-dependent cases skipped without a DSN, 0 failed. Separate configured database evidence follows. |
| `.venv-integrations/bin/python -m pytest tests/test_planner.py tests/test_planner_provider_errors.py tests/test_business_planning.py tests/test_business_retrieval.py tests/test_business_investigations.py tests/test_workflow_population_acceptance.py tests/test_automatic_inputs.py -q --disable-warnings` — `/tmp/overview-resume-retrieval.log` | 151 passed, 4 subtests passed, 0 failed, 0 skipped. |
| `.venv-integrations/bin/python /tmp/run-overview-resume-postgres.py` — `/tmp/overview-resume-final-postgres-tests.log` | 46 passed, 0 failed, 0 skipped: durable automation, Overview recurrence and PostgreSQL/Mongo query pushdown on disposable databases. PostgreSQL used a socket-only instance and non-superuser test role. |
| `.venv-integrations/bin/python -m pytest tests/test_overview_report_updates.py -xq --disable-warnings` — `/tmp/overview-resume-report-update.log` | 4 passed, 0 failed, 0 skipped. A redundant helper-only test was subsequently removed; the three substantive integration/authority cases remain in source. |
| Frontend `npm test -- --reporter=dot` — `/tmp/overview-resume-qualified-frontend.log` | 556 passed across 85 files, 0 failed. |
| Frontend `npm run typecheck` — `/tmp/overview-resume-final-types.log` | Passed. |
| Frontend `npm run lint -- --ignore-pattern '**/.next-*/**'` — `/tmp/overview-resume-final-lint.log` | Passed. Unfiltered lint scans retained generated rollback artifacts and fails on those generated files. |
| Isolated frontend `npm run build` — `/tmp/overview-resume-final-build.log` | Passed; build `EiDLCCE7beRH3coeDHj3o`. Source matched the checkout at browser qualification. |
| Frontend `BUILDER_E2E_FRONTEND_DIR=/tmp/praxi-overview-release-udo1qsf8/frontend ./node_modules/.bin/playwright test --config playwright.overview-automation.config.ts` — `/tmp/overview-resume-final-browser.log` | 10 passed, 0 failed: desktop/mobile consent, refresh, cancellation, explicit retry after failure, uncertain-submit identity preservation and legacy no-ID query flows. API responses are controlled fixtures. |
| `.venv-integrations/bin/python scripts/validate_contracts.py` | Shared schemas and fixtures valid. |
| `.venv-integrations/bin/python scripts/generate_ui_contracts.py --check` | Generated frontend contracts match canonical schemas. |
| `/home/raf/.nvm/versions/node/v22.23.3/bin/openspec validate unified-overview-automation --type change --strict --json` | 1 change passed, 0 issues. |
| `git diff --check` | Passed before this documentation-only handoff. |

Initial failed checks were corrected: HTTP request correlation is independent of
persisted business idempotency; the planning-status lookup now tolerates stores
without a planning queue table; asynchronous frontend status access now typechecks.
An initial native writer fixture with retries was denied by Registry; the fixture
now explicitly registers zero retries, preserving the write safety boundary.

## Final deployment qualification

The earlier tool approval usage limit was resolved. The previously pending
combined binding regression completed: **73 passed, 0 failed, 0 skipped**:

```sh
.venv-integrations/bin/python -m pytest tests/test_overview_report_updates.py tests/test_action_evidence_references.py tests/test_scalar_input_bindings.py tests/test_connected_action_plans.py tests/test_query_envelope_bindings.py -q --disable-warnings
```

The final routing/API/queue/temporal/runtime/report-update suite, including monthly
recurrence, completed: **62 passed, 0 failed, 0 skipped**:

```sh
.venv-integrations/bin/python -m pytest tests/test_overview_automation.py tests/test_overview_automation_api.py tests/test_overview_automation_integration.py tests/test_overview_planning_queue.py tests/test_overview_report_updates.py -q --disable-warnings
```

Logs: `/tmp/overview-deploy-binding.log` and `/tmp/overview-deploy-final.log`.
Six copied-store baseline/candidate account rehearsals passed; candidate rehearsals
advertised enabled routing. The deleted historical Simpson workflow retained its
existing tombstone and denial. Exact source/frontend manifests and application-only
rollback were prepared before rollout. Authenticated hosted checks, six read-only
browser journeys and history/credential/configuration preservation passed afterward.

The deployment examples added first/named-day monthly recurrence to the internal
structured route and existing cron conversion. Missing month day or time still
requires clarification. No new scheduler or canonical shared schema was introduced.

No paid model interpretation, live workflow submission, real email or spreadsheet
mutation was performed by verification. Controlled acceptance does not establish
live-model accuracy for every wording, every tenant's business mappings or every
external provider outcome. The user can now test through the deployed Overview.
