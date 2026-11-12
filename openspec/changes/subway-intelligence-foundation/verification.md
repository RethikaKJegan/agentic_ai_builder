# Subway Phase 1 implementation and verification

Implemented locally on 11 November 2026. No deployment, service restart, live
model request, email, company-record write, production migration or ontology
publication was performed. Existing uncommitted Knowledge Map/context work was
preserved. Canonical shared contract files and stored ontology artifacts are unchanged.

## Root causes and changes

| Files | Reproduced problem and resulting behavior |
| --- | --- |
| `workflow_api/subway_queries.py`, `workflow_api/overview_automation.py` | Lexical source ranking missed business vocabulary; Overview used generic metadata even with the reviewed Subway executor installed. The existing intent-model request now receives a bounded, source-backed Subway concept/alias/field/relationship index and returns a validated selection. Only the selected metadata reaches query planning. No extra semantic model service, synonym dictionary or orchestration engine was introduced. |
| `workflow_api/action_plans.py` | New Subway plans exposed competing generic and Subway schemas and instructions. The reviewed Subway path is now authoritative for new v4 plans. Generic services/connectors remain installed for other tenants and historical workflows. Historical revision reconstruction retains its recorded capability family. |
| `workflow_api/goal_inputs.py` | Query-envelope normalization only supported the generic executor. Both exact schema-compatible planner/tool pairs now normalize the query child. A unique existing planner also supplies a missing internal query binding and dependency. Multiple possible planners are never guessed. |
| `workflow_api/business_planning.py` | Source-cited knowledge was disconnected from selected query metadata. Retrieval can now select exact concept and relationship IDs, retain relevant descriptive rules, and return hash-checked excerpts from content already present in the owned snapshot/evidence-resolution sources. Metadata-only documents are not treated as extracted content. Simpsons' default retrieval path remains compatible. |
| `runtime/action_plans.py` | Subway model output lacked the generic path's semantic validation. It now checks the selected dataset/field/join scope and exact server-resolved reporting windows before tool dispatch. Read receipts must match the canonical query digest, tenant and ontology pin. |
| `workflow_api/workflow_knowledge.py` | Subway reads did not record equivalent concept/field/query provenance. Existing immutable metadata and action-instance storage now retain exact Subway mappings and join checks. Count-only usage records dataset identity rather than claiming unrelated field use. Report consumption retains upstream provenance; delivery tools do not inherit it. |
| `workflow_api/planning_jobs.py` | Unexpected exceptions collapsed into an uncorrelated `PLANNING_FAILED`. Logs now retain request/correlation/job IDs, typed codes, exception classes and stack locations without exception bodies, prompts, model output or bindings. Typed SQLite contention and planner failures remain distinct. Queued correlation metadata is removed before canonical dispatch. |
| `frontend/src/domain/workflow-knowledge.ts`, `frontend/src/features/investigations/QueryEvidence.tsx`, `OverviewAutomationReview.tsx` | Existing displays only understood generic query receipts and suppressed business-meaning questions. The same map/results layout now handles Subway fields, exact joined relationship receipts, coverage and currency warnings. Explicit business-meaning clarifications are displayed in the existing review. No frontend redesign. |

Monetary min/max now receive the same currency separation guard as sum/average.
Missing recorded currency is explicitly qualified. Scalar joins retain existing
native/schema-backed reference conversion and measured unmatched coverage; no
store/site identity, vendor join, currency conversion or approval policy was added.

The old reported `PLANNING_FAILED` incident cannot be conclusively reconstructed
from its generic error alone. The implementation fixes reproducible integration
defects; it does not claim SQLite locking caused that historical incident.

## Existing components reused

Overview routing and durable planning jobs, the existing OpenAI Responses planner,
Business Ontology and source metadata services, client knowledge packages,
Registry policy/assignments, CrewAI, GraphRunner, existing query executor, immutable
workflow/run records, source-mapping inspection, and current Overview/results/map UI.
No Subway business-case lifecycle was introduced. New Phase 1 Subway routing is
for immediate read-only work; recurring/delayed requests are explicitly unsupported
on this path rather than silently scheduled. Existing saved workflows are not rewritten.

## Acceptance evidence

`tests/test_subway_intelligence.py` uses isolated temporary stores and explicitly
synthetic operational rows. It exercises the actual dedicated-client assertion,
normal Overview planning-job API, existing OpenAI SDK/strict planning transport
with an HTTP mock, actual Registry/CrewAI/GraphRunner, complete query execution,
persisted completion, source receipts, and Knowledge Map inspection endpoint.
Controlled transports establish executable integration, not live model judgment
or a fact about genuine Subway records. Fixture-local actual connector receipts
must not be interpreted as production source observations.

Covered scenarios include outlet terminology with ambiguous spending; dated
purchase-order count/min/max/average; complete scalar approval joins and supplier
name grouping; missing store/site identity and approval semantics; invalid/foreign
metadata; exact query-window preservation; currency separation; absent internal
bindings; ambiguous planner dependencies; source-cited definition-only requests;
typed contention diagnostics; count-only provenance; and retained completion.
Existing query tests additionally cover filtering beyond the first 25 records,
sorting/pagination, empty results, duplicate join targets, null aggregates,
exact averages, stale authority and cross-tenant denial.

### Commands and results

All backend commands use the existing `.venv-integrations/bin/python -B -m pytest
-q -p no:cacheprovider`, temporary fixture persistence, `CREWAI_TESTING=true` and
`CREWAI_TRACING_ENABLED=false`. Set `OTEL_SDK_DISABLED=false` for the existing
actual in-memory OpenTelemetry span test. No test DSN or live provider target was used.

- Core group: **80 passed, four passing subtests**. Modules: `test_subway_intelligence`,
  `test_subway_full_queries`, `test_workflow_ontology_usage`, `test_subway_dump_grounding`,
  `test_subway_coverage_audit`, `test_overview_planning_queue`, `test_deleted_planning_retry`,
  `test_planner_provider_errors`. Log: `/tmp/subway-phase1-core-final.log`.
- Compatibility group: **262 passed, 28 passing subtests**. Modules: `test_runtime`,
  `test_goal_planning`, `test_workflow_query_integration`, `test_business_planning`,
  `test_overview_knowledge_routing`, `test_overview_automation`,
  `test_overview_automation_integration`, `test_simpsons_client_isolation`,
  `test_subway_client_auth`, `test_data_queries`, `test_registry`.
  Log: `/tmp/subway-phase1-regressions-final.log`.
- Final Subway follow-up after count-only provenance tightening: **15 passed**.
  Fourteen overlap the core group; one additional case verifies that count-only
  execution records identity without claiming unrelated source-field use.
  Log: `/tmp/subway-phase1-acceptance-final.log`.
- Final monetary/date follow-up: **three passed** (overlapping cases), verifying
  that monetary min/max reject text amounts while date min/max and exact
  sum/average remain valid. Log: `/tmp/subway-phase1-monetary-final.log`.
- These groups cover **343 distinct backend test cases**: 80 core + 262
  compatibility + one additional count-only case. Follow-up runs and passing
  subtests are not added as independent cases.
- Frontend: `npm test -- --reporter=dot`: **602 passed in 89 files**.
  `npm run typecheck` and `npm run lint`: **passed**.
- Production build: **passed** in the disposable source copy recorded by
  `/tmp/subway-phase1-build-path`; active `frontend/.next` was not rebuilt.
- `BUILDER_E2E_FRONTEND_DIR=<isolated-copy>/frontend node
  node_modules/@playwright/test/cli.js test --config playwright.subway-intelligence.config.ts`:
  **12 passed**. Desktop/mobile Subway Overview → results → Knowledge Map → reload,
  existing three-tenant map checks, and generic query/clarification flows.
  Log: `/tmp/subway-phase1-browsers-final.log`.
- Shared schema validation, generated UI contract drift, strict scoped OpenSpec
  validation and `git diff --check`: **passed**. The cached OpenSpec CLI is at
  `/home/raf/.npm/_npx/abab5bd700860149/node_modules/@fission-ai/openspec/bin/openspec.js`.

Initial diagnostic runs are not clean qualification: synthetic provisioning was
corrected to use actual client markers, a test-only manifest and the existing
trusted package-size allowance; receipt verification was corrected to use the
query service's canonical digest; content extraction was corrected for normalized
source whitespace. One compatibility run failed its span test because the SDK
was globally disabled; the complete group passed with its required SDK enabled.
Browser fixtures were aligned with the already-existing Details disclosure and
Reports tab while preserving account, coverage, blocked-query and reload assertions.
No product control was restored or weakened to satisfy an obsolete selector.

## Remaining evidence and qualification limits

- No live OpenAI paraphrase/answer-quality acceptance was performed. The existing
  transport, schema validation, plans and execution are tested with controlled
  model responses; arbitrary natural-language understanding is not guaranteed.
- The repository does not establish one authoritative meaning of spending, an
  automatic central-store/finance-site identity, a universal pending-approval
  definition, or a universal available-budget measure. Such questions retain
  precise clarification/limitations instead of fabricated metrics or joins.
- Supplied code rules remain descriptive implementation evidence, not independent
  company policy. Supplier-name grouping does not prove linkage to central vendor IDs.
- No new currencies, exchange rates, deduplication rules or timezones were invented.
  Native record counts retain their collection grain. Separate collection reads
  do not provide an atomic cross-database snapshot.
- Live restored-source execution, production load/soak, PostgreSQL migration,
  provider consent/delivery, deployment and production readiness are not qualified
  by these tests. Live credentials and existing client data/configuration were not changed.
- Phase 2 autonomous/adaptive reasoning and Phase 3 events, schedules, emails and
  external writes remain outside this implementation. Their existing shared
  infrastructure was not replaced or enabled for Subway by this work.
