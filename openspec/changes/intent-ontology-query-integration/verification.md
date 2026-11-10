# Intent and ontology query integration — verification, 10 November 2026

## Diagnosis and evidence limits

The supplied correlation ID `20ee6da1-6bae-48a1-8bc8-bc35a82a1293` was not present in the available service journal output. Failed action proposals are not retained as successful business compositions. Exact historical intent, metadata pins, complete proposal and model transport for that ID therefore could not be recovered; no exact request attribution is claimed.

A Simpson service diagnostic at 2026-11-09 17:18:55 UTC records node `prepare_limited_report`, capability `content.prepare`, no dependencies, and binding `{kind: context, key: validated_context, path: [validated_context], target: [data]}`. The exact error text originates in `workflow_api/action_bindings.py:binding_value`, called by `validate_plan` during connected planning. The missing key was `validated_context` INSIDE that namespace; available context entries must be referenced by actual child keys. The model treated the namespace as its own child and no upstream result supplied data. This diagnostic selected a report model, not a complaint reader. The exact malformed binding and user prompt are reproduced in the new acceptance test.

Separately, connected planning called DataQueries.catalogue(auth) without its objective. The catalogue serialized all authorized tables before any existing ontology retrieval. The 120000-byte guard removed the generic query capability. The observed fallback report and unavailable generic capability are compatible with this failure mode, but unavailable historical pins prevent proving the model's full causal decision for the supplied correlation ID. Existing no-ID case-reader correction remains covered independently. No complaint ID is invented and no required schema input is made optional.

## Reused architecture and implementation

- Existing OpenAI `plan_actions` interprets the objective and dependencies; existing CrewAI strict query model proposes executable field IDs and operations. No second intent/orchestration service was created.
- Existing DatabaseWorkflows/KnowledgeRetrieval provides owned persistent metadata index, reviewed concepts, descriptions, terminology, semantic relationship context, bounded candidates and deterministic declared/accepted paths.
- Existing Registry still validates permission, side effect, credentials, schemas, tool version and budgets. Existing DataQueries/DataQueryJobs, GraphRunner leases, checkpoints, idempotency and evidence/report rendering execute downstream work.

Files changed for this correction:

| File | Change |
| --- | --- |
| workflow_api/data_queries.py | Goal-aware catalogue through existing retrieval; retain reviewed mappings, source revision and semantic discovery warnings; separate model byte bounds from backend validation. Questions reuses the same objective filtering. |
| workflow_api/kg_retrieval.py | Internal source projection before existing budget; exclude only fields already unsupported by the query engine. Default retrieval callers are unchanged. |
| workflow_api/data_source_routes.py | Wire existing DatabaseWorkflows retrieval into DataQueries. |
| workflow_api/action_plans.py | Pass objective during discovery; one metered correction for invalid internal context/configuration/evidence bindings. |
| workflow_api/action_bindings.py | Identify missing namespace/key/path/action/capability and retain existing strict validation. |
| workflow_api/workflow_queries.py | Pin objective dataset scope and reject expansion even to other owned datasets; existing saved workflows without this new list remain compatible. |
| tests/test_intent_query_discovery.py | Oversized scopes, both business entities, reviewed synonyms/relationships, missing mappings, foreign owner and untruncated wide-schema refusal. |
| tests/test_workflow_queries.py | Objective-scope rejection before reads. |
| tests/test_workflow_query_integration.py | Exact malformed binding, literal prompt, real ontology retrieval, oversized scope, CrewAI query/report and independent aggregate checks. |

No frontend source, shared contract, database schema, scheduler or runtime engine was changed in this correction. Already present Subway evidence-resolution source/artifact changes were preserved, included in the source manifest and checked with their seven existing tests; they were not rewritten by this task. Unrelated workspace files were preserved.

## Metadata boundary measurements

Copied current stores, no network or business-row reads:

| Account/objective | Full query catalogue bytes | Scoped planner document bytes | Result |
| --- | ---: | ---: | --- |
| Operator / complaint statistics | 226508 | 79347 | Generic query available |
| Simpson / literal original prompt | 226032 | 79415 | Generic query available; tickets retained |
| Subway / purchase-order statistics | 264066 | 81192 | Generic query available; purchaseorders retained |

The existing 120000-byte query catalogue limit was preserved. A first projection reused raw profiling descriptors and omitted tickets under the retrieval budget. Restricting descriptors to existing executable scalar fields fixed that measured integration issue. No supported scalar fields within retained datasets were truncated. Existing bounded candidate omissions and warnings remain explicit; no arbitrary join is inferred. If the complete relevant source cannot fit, the existing actionable KG_RETRIEVAL_LIMIT remains.

## Original-prompt and cross-customer acceptance

The literal original prompt is tested through the real existing ontology index, Registry, action validator/compiler, CrewAI adapter, durable graph query wait/resume, query engine and report model boundary with controlled transports. A 95-table irrelevant catalogue expansion exceeds 120 KB. Only the complaint dataset reaches the query planner. The first proposal deliberately repeats the observed bad context binding; exactly one correction creates data.plan_query -> workflow_data_query -> content.prepare without a complaint ID or external write action.

603 fixture records include values beyond row 500 and a null. Independent Decimal calculations verify the inclusive 0–100 range: count 404, minimum 0, maximum 100, average 50. The engine serializes exact decimal results as strings. A first strengthened fixture asserted integer min/max; its transport assertion failed and was corrected to the existing exact-decimal wire contract without changing engine behavior or weakening numeric expectations. No emails or Sheets writes occur in this original-prompt test. These are fixture statistics, not customer results.

Simpson and Subway population fixtures independently verify count/min/max/avg/sum over their own configured numeric measures. Existing single-case planning, selected Google connection, missing recipient clarification, restart/reattachment, recurring query freshness, exact consent, duplicate trigger prevention, tenant isolation and recovery regressions remain covered. Paraphrase support is bounded by actual metadata vocabulary/reviewed synonyms; no universal natural-language accuracy claim is made.

## Commands and outcomes

All Python commands use `.venv-integrations/bin/python -m pytest`. Logs are private under `.local/intent-query-deploy-20261110/`.

- `tests/test_intent_query_discovery.py tests/test_workflow_queries.py tests/test_workflow_query_integration.py -xq`: **27 passed**, query-combined-final.log.
- `tests/test_connected_action_plans.py tests/test_goal_planning.py tests/test_tenant_google.py tests/test_agent_memory_recovery.py -xq`: **146 passed**, planning-regression.log.
- `tests/test_data_queries.py tests/test_data_query_jobs.py tests/test_workflow_population_acceptance.py tests/test_kg_retrieval.py tests/test_semantic_kg.py tests/test_ontology_foundation.py -xq`: **133 passed, 3 PostgreSQL cases skipped** without a DSN, engine-regression.log.
- `tests/test_ontology_foundation_postgres.py tests/test_data_query_jobs.py -k postgres -q` with BUILDER_TEST_POSTGRES_DSN pointing only to the owned disposable Unix-socket PostgreSQL cluster and non-superuser task_test: **30 passed, 21 deselected**, postgres-tests.log. Cluster stopped after tests.
- `tests/test_subway_evidence_resolution.py -q`: **7 passed**, knowledge-regression.log.
- `npm run test -- src/features/investigations`: **62 passed**, frontend-tests.log.
- `npm run typecheck`: passed, types.log.
- `npm run lint` in clean isolated source: passed, lint-clean.log. Running lint in the live frontend initially included retained `.next-before-unified-20261109` generated rollback types; those are artifact files, not changed source. No lint rule was disabled.
- `npm run build` in isolated production source with actual frontend configuration and required repository-level shared/ontology imports: passed, build.log. The initial isolated directory omitted these external fixture imports; adding the real repository dependencies fixed that staging error. No application import was removed.
- `BUILDER_E2E_FRONTEND_DIR=<isolated production frontend> npx playwright test -c playwright.workflow-queries.config.ts`: **2 passed**, browser.log. APIs are controlled fixtures; verifies no-ID submission, selected account, evidence coverage and refresh on desktop/mobile.
- `scripts/validate_contracts.py`: schemas/fixtures valid; `openspec validate intent-ontology-query-integration --type change --strict --json`: valid; `git diff --check`: passed.

An initial monolithic backend run showed a failure marker and was interrupted while isolating it; interruption hit pytest fixture teardown and prevented a useful failure summary. That run is not reported as passing. A standalone integration rerun, affected combined rerun (27 passed), then the final strengthened combined rerun (27 passed) passed. Its initial marker was not reproducible; no proven cause is invented. The completed split release suites above provide current qualification evidence.

## Remaining qualification limits

No paid OpenAI call, live natural-language workflow submission, email, Sheets write or provider mutation was made. Paid live-model interpretation and a real-source evidence report remain pending separate authorization. Current metadata contains multiple possible hour measures (including string-valued fields); this release does not certify a unique reviewed customer operating-hours definition or enable implicit coercion. Unsupported/ambiguous measures still require clarification. No customer statistics were fabricated.

Natural-language schedule creation, runtime query clarification/resume and recurring relative-date semantics remain separate unfinished scope from the prior unified specification. Historical shared-store integrity audit and earlier full-platform qualification gaps remain unresolved. This release fixes initial discovery/binding integration and does not certify full production readiness.
