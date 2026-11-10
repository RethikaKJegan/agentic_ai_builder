# Workflow query clarification — 10 November 2026

## Actual failure

Read-only inspection identified Simpson run `run_018cdc5a65a24d44b3acfbfe1682f251`, composition `composition_cdd1ef2c9e9a8e3633882b9c`. The query-planning action completed. Its typed query contained a nonempty clarification asking for the precise complaint operating-hours field and unit. Candidate metadata included numeric tickets.hmr, string complaintRecord.hmr and other distinct hour measures. No field was confirmed as the requested measure in the query catalogue. The query adapter correctly refused to invent a meaning and stopped before submitting a data-query job or reading source rows. Report and email actions remained pending.

The actual integration defects were presentation and recovery: ACTION_INPUT_REQUIRED became a failed execution, the question was available only inside persisted query inputs, and CompositionPresentation treated every tool in a workflow allowing a later email as an external write. It therefore incorrectly requested reconciliation for a read-only query. The user's instruction explicitly allowed an explanation of missing definition, so a generic execution error was inappropriate.

Existing Simpson code-level ontology distinguishes primary reported complaint hours from alternate ticket hours, and some source measures are strings. This release does not silently select the alternate numeric measure, equate distinct business meanings, or introduce implicit numeric coercion. The unresolved definition remains real; it is now presented accurately.

## Changes

- workflow_api/workflow_queries.py: explicit QueryClarification signal; read-only extraction of saved questions, including older failed runs. Tool output schemas and shared contracts unchanged.
- runtime/graph.py: trusted read-only query clarification persists a blocked run and needs_input action, original question, not_performed effect status and an event before any query job/source read. The existing runtime state machine, leases and budgets remain authoritative. It does not complete downstream report/email nodes or replay the action.
- runtime/recovery.py: use sealed per-action side-effect contracts for connected tools; exclude reviewed reads from uncertain-write inspection. Unknown/malformed legacy metadata retains conservative write handling.
- workflow_api/composition_presentation.py: surface the actual question through existing task result fields and needs_input state. Historical run documents remain untouched. Existing/uncertain write attempts still require reconciliation and disable inline clarification generation.
- frontend/src/api/compositions.ts: optional backward-compatible can_clarify projection flag.
- frontend/src/features/investigations/QueryClarification.tsx: show the question, accept an explicit field/unit definition, and generate a new reviewable plan through the existing API. Preserve original selected Google connection, client, resources and supplied inputs. Existing idempotent command handling prevents duplicate submissions and controls uncertain responses. No provider effect is executed by this form.
- ConnectedPlan.tsx and CompositionPanels.tsx: normal clarification display, question in task/report details, and suppression of the misleading generic failure banner only when the server allows safe clarification.
- tests/test_workflow_query_clarification.py; frontend query-clarification.test.tsx; extended frontend/e2e/workflow-queries.spec.ts: positive/negative clarification, recovery and account-preservation acceptance.

A new definition prepares a separate reviewed workflow. In-place resumption with changed query bindings is not introduced. The original run, approvals, history and budgets are preserved. Supplying a definition remains subject to current fields/types, permissions and query limits; unsupported conversions or joins are not enabled.

## Verification commands and results

Python commands use `.venv-integrations/bin/python -m pytest`. Private logs are in `.local/query-clarification-deploy-20261110/`.

- `tests/test_workflow_query_clarification.py -q`: **7 passed**, clarification-final.log. Verifies no query jobs/reads/emails, preserved checkpoints on restart, historical projection without rewriting, actual-write reconciliation, and fail-closed malformed legacy metadata.
- `tests/test_workflow_query_clarification.py tests/test_workflow_queries.py tests/test_workflow_query_integration.py tests/test_composition_presentation.py -xq`: **50 passed**, query-regression.log. This run predates only the final malformed-legacy-metadata hardening, which the final seven checks cover.
- `tests/test_agent_memory_recovery.py tests/test_investigation_recovery_details.py tests/test_connected_action_plans.py -xq`: **93 passed**, recovery-final.log. An initial run stopped after 16 passes with a SQLite contention/lease-heartbeat failure in targeted recovery. The isolated case passed; the full suite then passed without weakening production checks. No application database or lease code was changed to suppress that failure.
- `npm run test -- src/features/investigations`: **65 passed**, frontend-tests.log. An initial new fixture had a missing closing brace; corrected before qualification.
- `npm run typecheck`: passed, types.log.
- `npm run build` and `npm run lint` in isolated frontend source with its real configuration and required shared/ontology files: passed, build.log/lint.log. The initial build exposed the same test-fixture syntax typo; the corrected build passed. No test credentials were deployed.
- `BUILDER_E2E_FRONTEND_DIR=<isolated production frontend> npx playwright test -c playwright.workflow-queries.config.ts`: **4 passed**, browser.log. Desktop/mobile scenarios verify persisted coverage and clarification, refresh, explicit answer before generation and selected-account preservation with controlled APIs.
- `scripts/validate_contracts.py`: valid. Strict OpenSpec validation passed. Diff whitespace checks passed. No database migration or SQL/storage adapter change; prior isolated PostgreSQL qualification remains separate evidence.
- Baseline/candidate copied-store startup: **six passed**, then all three final candidate rehearsals passed after conservative legacy-metadata hardening. Network/workers were disabled and protected rows unchanged. The actual failed Simpson run was checked on the copied store and correctly projected as needs_input with its saved question.

## Live verification and limits

Authenticated public HTTPS checks passed for operator, Simpson and Subway: correct scope, Business Investigation, Questions, generic query tool and worker health. Six desktop/mobile journeys passed with all API mutations blocked. Both Simpson journeys additionally reopened the user's actual composition, verified the Clarification needed heading, original tickets.hmr question, required definition field and absence of the erroneous reconciliation instruction, then refreshed and verified persistence. No model request or external provider action was submitted.

All five services are active with zero automatic restarts. Error-priority journals since activation have no entries. Existing histories/jobs, encrypted Google/source credentials and credential/configuration hashes are preserved.

The actual measure definition remains unresolved; no customer statistics are reported and no field is guessed. A paid/live-model clarified rerun was not performed. The new form prepares a fresh reviewed plan when the user supplies a supported definition. Arbitrary prompt accuracy, implicit casts, unsupported joins, automatic natural-language schedules, in-place query clarification/resume and historical shared-store audit remain outside this release's claims.
