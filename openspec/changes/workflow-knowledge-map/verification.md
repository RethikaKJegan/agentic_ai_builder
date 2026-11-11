# Knowledge Map implementation and verification

## Scope and reused interfaces

Frontend-only visualization and workflow presentation, using existing authenticated
`business-ontology/v1`, version `/knowledge`, action-plan, composition-view and
`runs/{id}/knowledge` APIs. Reused the existing React Flow/Dagre canvas libraries,
Sheets/dialog components, Google account display, query-evidence renderer,
composition inspector and idempotent orchestration command handler. No backend
implementation, persistence, scheduler, retrieval, planner, prompt, Registry or
CrewAI execution changes. Backend and shared-contract file hashes and the four
backend/worker process IDs were recorded and verified unchanged after release.

## Files changed for this feature

| File under frontend/ unless stated | Reason |
| --- | --- |
| src/api/knowledge-map.ts | Typed projection of the existing knowledge inspection response. |
| src/api/client.ts | Read-only knowledgeSnapshot method using the existing endpoint. |
| src/api/business-ontology.ts | Accept tenant ontology IDs generically in frontend validation. |
| src/domain/workflow-knowledge.ts | Exact-reference adapter, version selection and evidence qualification. |
| src/domain/workflow-knowledge.test.ts | Generic tenant, execution, history, synthetic-data and upstream-consumption tests. |
| src/features/investigations/KnowledgeMap.tsx | Scoped loading, workflow/full graph, groups, search, step filtering, pan/zoom and concept inspector. |
| src/features/investigations/KnowledgeMap.test.tsx | Interaction, historical fallback, overlapping IDs and stale asynchronous response isolation. |
| src/test/fixtures/knowledge-map.ts | Three synthetic tenant fixtures with overlapping concept, workflow and run identifiers. |
| src/features/investigations/ConnectedPlan.tsx | Unified tabs, Details, Background, Validate and blue Run with explicit review; scope/run reset. |
| src/features/investigations/ConnectedInvestigation.tsx | Remove duplicated heading on an open workflow. |
| src/features/investigations/OverviewAutomationReview.tsx | Avoid repeating the request heading and objective above an open workflow. |
| src/features/investigations/orchestration.test.tsx | Updated tab/navigation expectations and explicit Run/schedule approval regression tests. |
| eslint.config.js | Exclude historical generated .next artifacts from source lint. |
| e2e/knowledge-map.spec.ts | Six production-artifact desktop/mobile journeys across three fixture tenants. |
| playwright.knowledge-map.config.ts | Isolated production frontend acceptance configuration. |
| tests/test_workflow_knowledge_isolation.py (repository root) | Direct three-tenant HTTP version/concept/mapping/owner tampering tests. |
| openspec/changes/workflow-knowledge-map/ and unified-workflow-data-queries/deployment.md | Scope, requirements, checks and hosted release record. |

## Authorization and tenant isolation

Ontology version lookups use authenticated workspace and owner in SQL; knowledge
inspection reuses that lookup and its authority checks. Composition reads similarly
select the authenticated workspace/owner, and run reads use existing runtime
authorization. No all-tenant catalogue is fetched. Frontend filtering is not the
security boundary. The UI validates document/plan scope and composition/run IDs.
Graph payloads are not persisted in browser storage or a cross-workspace cache.
Components reset by subject, workspace, composition, workflow version and run;
effect cleanup ignores old requests. Overlapping fixture IDs expose unsafe reuse.

Actual hosted checks, separately authenticated:

| Account | Concepts | Relationships | Own ontology/knowledge | Foreign version/knowledge/workflow |
| --- | ---: | ---: | --- | --- |
| Simpsons | 79 | 48 | HTTP 200 | HTTP 404 |
| Subway | 54 | 67 | HTTP 200 | HTTP 404 |

A foreign saved Simpsons run requested through Subway returned 404. Caller-supplied
workspace query parameters did not override authenticated scope. The existing
public proxy rejects colon-containing individual-concept URLs with HTTP 400;
direct backend HTTP tests verify owner/version isolation on those routes. The map
uses the supported version knowledge response for node definitions and mappings,
so it does not need that restricted per-concept URL. No proxy rule was relaxed.
Synthetic third-tenant tests prove rendering genericity, not a third live account.

## Evidence rules and historical limitations

An exact saved required_ontology, concept evidence token or known mapping reference
can establish Planned. A completed reader must have a backend-verified receipt,
an exact saved source-evidence mapping/record reference and an available pinned
ontology version to establish Executed. Synthetic scenario outputs cannot establish
actual usage. Completed content steps can inherit usage only with recorded
source_reference input provenance consuming an associated upstream result. Email,
Calendar and Sheets steps do not acquire ontology usage from their inputs alone.

Successful queries, field labels, similar names, nearby ontology concepts and
running steps are not proof of concept usage. Relationship highlighting requires
an explicit relationship reference; two used endpoint concepts do not prove a join.
Read coverage/pagination remains separate from concept usage and is displayed from
recorded receipts. Source fields are labelled only through exact catalogue IDs.

The adapter prefers a saved ontology pin. When unavailable, it labels the current
ontology as a historical fallback and never upgrades current definitions into
executed historical usage. Missing provenance displays “Usage history unavailable”
and source-only references display “Concept association unavailable.” Latest live
workflows without saved mappings can explore their full ontology, but will not
show invented execution highlights. No historical associations were backfilled
and no new backend provenance persistence was added.

## Commands and results

Commands below run from frontend/ unless stated otherwise.

| Command | Result |
| --- | --- |
| npm test | 581 passed across 88 files |
| npm test -- src/features/investigations/KnowledgeMap.test.tsx src/domain/workflow-knowledge.test.ts | Final layout/adapter recheck: 15 passed; subset of suite |
| npm run typecheck | Passed |
| npm run lint | Passed; generated historical artifacts excluded |
| npm run build | Passed in isolated frontend staging; live artifact was not built in place |
| npx playwright test --config=playwright.knowledge-map.config.ts | Final production artifact: 6 passed, three tenants × desktop/mobile |
| .venv-integrations/bin/python -m pytest tests/test_account_knowledge.py tests/test_account_knowledge_api.py tests/test_business_knowledge.py tests/test_business_investigations.py tests/test_connected_action_plans.py --basetemp=/dev/shm/knowledge-map-api-checks-20261111 -q (root) | 138 passed |
| .venv-integrations/bin/python -m pytest tests/test_workflow_knowledge_isolation.py --basetemp=/dev/shm/knowledge-map-http-isolation-20261111 -q (root) | 1 passed |
| .venv-integrations/bin/python scripts/validate_contracts.py (root) | Passed |
| openspec validate workflow-knowledge-map --type change --strict --json (installed Node 22 runtime) | Passed |
| git diff --check (root) | Passed |

Browser acceptance covers graph loading, node selection/definitions/mappings,
relationship navigation, workflow/full views, module groups, search, step selection,
zoom/fit, Details, Background, Reports, desktop/mobile overflow and page errors.
Unit tests cover plan validation without autoexecution, explicit Run confirmation,
duplicate-click prevention and scheduled approval without immediate execution.
No live Run/Validate or exact-payload approval was submitted during verification.

Post-deployment real browser checks: four passed, Simpsons and Subway on desktop
and mobile; 79/54 authorized nodes rendered, no page errors or horizontal overflow.
All backend mutations were blocked in these journeys. Public unauthenticated
login/app/API gates and authenticated read-only checks passed for all three
existing account routes. No paid model request or provider write was triggered.

## Deployment and rollback

Deployed build `LwjiQ6zW7R_v9SiWeofP8` to https://praxi.bellcorpstudio.com/ after the
user explicitly approved frontend deployment. Only the frontend service restarted.
Prior static chunks were retained for existing tabs; the prior complete frontend
artifact is retained at `.local/knowledge-map-ui-20261111/previous.next`.
Source and artifact manifests, configuration hashes, backend baseline, authenticated
isolation results and screenshots are retained privately beside it. Application
rollback swaps the previous artifact back and restarts only the frontend; no
database restoration or backend rollback is required.
