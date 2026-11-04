# Dynamic investigation UI verification — 4 November 2026

## Implemented

The existing overview prompt, investigation list and investigation workspace now
connect shared preparation, registered capability composition, canonical workflow
lifecycle and persisted delegation/CrewAI execution. New compositions use durable
jobs; historical investigation links keep their old path. The session capability
flag prevents an older backend from receiving unsupported composition requests.

The UI renders actual task dependencies, independent read paths, coordinator,
external action gates, saved statuses, node results, report citations, optional
knowledge/agent/tool/memory/outcome details, missing setup inputs, explicit request
regeneration, cancellation and eligible recovery. Rename/delete uses the existing
three-dot pattern. Read-only client-package selection and explicit typed connected
resources are available. Source observations and generated scenario evidence stay
qualified; no company approval, policy or physical identity is invented.

Normal permission/revision/idempotency/Registry checks remain authoritative. Saved
historical context can be inspected after metadata changes without permitting stale
execution. Active runs block deletion, and deleted workflows cannot execute using
an old approved revision. External actions retain independent runtime gates.

## Automated verification

- Broad backend suite: **222 passed, 24 subtests passed** (`test_composition_presentation`,
  `test_business_composition`, `test_agent_memory_recovery`, `test_investigation_jobs`,
  `test_live_providers`, `test_planner`, `test_runtime`, `test_workflow_api`).
  Final protocol/usage fixes received additional focused checks: **97 passed,
  18 subtests passed** for presentation, composition and runtime; **4 passed** for
  citation/usage guards and configured model policy; **3 passed** for durable
  explicit-action handling and strict selection. These suites overlap and are
  not additive counts. Final configured-launcher/presentation/actual CrewAI bridge
  follow-up: **45 passed**. Final citation/actual CrewAI checks: **2 passed**.
- Frontend: **464 tests passed**, TypeScript and ESLint passed.
- Production frontend build passed.
- Browser integration: **12 passed**, desktop and mobile, including six new dynamic
  flows and six legacy/rename/delete compatibility flows. Screenshots inspected.
- Canonical contract validation, generated UI contract drift check and scoped strict
  OpenSpec validation passed. Shared workflow/agent/tool schemas were not modified.
- `git diff --check` passed.

Logs are local operator artifacts in `/tmp/dynamic-ui-*.log`, not company evidence
or distributable test fixtures. Existing unrelated and prior-phase dirty work was
preserved. Deprecated FastAPI lifecycle/JSON Schema resolver warnings remain.

## Actual configured-provider acceptance

An isolated application database/registry copy used actual configured OpenAI and
CrewAI with the previously authorized mapped **A-2022-12-013** complaint/linked
inspection comparison. Normal HTTP session/job preparation, canonical draft save,
validation, approval, execution and UI projection were exercised. No arbitrary
attachments, company-data writes, live application changes or Google effects.
Provider response storage was disabled.

Successful receipt:

- Composition: `composition_730fa6a1890756034e2ef6a5`
- Run: `run_276527d99b9f4d4280f886a43e07fafe`
- Status: **completed**; **4/4 task checkpoints**, source records available,
  **2 mapped read tool calls**, no final error.
- One model capability-selection call, followed by 10 runtime model turns. Actual
  runtime usage was recorded. Scope remained read/compare/report only.
- Private receipt/view under
  `.local/dynamic-investigation-checks/check-h7tszrdd/`; do not commit copied DBs,
  private snapshots or OAuth material.

Earlier isolated live attempts exposed real integration defects that fake-model
checks had not caught. They did not modify production state. Corrections:

1. Register the mapped read tool/provider in the configured launcher and preserve
   that connector when installing Google connectors.
2. Use the configured agent model and a strict capability-ID selector; the
   deterministic compiler owns the canonical graph. Procurement's planner wrapper
   forwards this protocol instead of falling back to model-generated graph JSON.
3. Distinguish unsupported operations from missing source facts in selector
   instructions: comparing/reporting incomplete evidence remains a supported goal.
4. Expose task-ID-only delegation proposals; runtime injects protected context.
5. Honor the existing server usage opt-out in both model capacity and actual usage
   settlement; keep call/time and enabled budget enforcement.
6. Bind analysis/finish schemas to the supplied record/field citation pairs and
   retain independent post-output source verification. Remove duplicate full
   citation evidence from the model context; expose its catalogue instead.
7. Carry explicit UI-selected operations through the durable job envelope and
   selection context; a planner cannot silently drop the requested action.

The successful pilot proves this bounded real case, not correctness for arbitrary
future goals or missing company facts. Provider outages, limits, revoked tools and
unsupported operations can still stop a run honestly.

Google read-only checks in a copied application database verified identity plus
HTTP 200 Gmail profile and primary Calendar reads for **two managed accounts**.
Four account rows existed; only those two were checked. Scope declarations were
inspected, but declared write scopes are not evidence that writes succeed. No
external or production-application writes occurred. Sheets resource acceptance
requires an explicit spreadsheet target.

## Outstanding operational acceptance

**Deployment update:** the website rollout below supersedes the earlier local-only
status. No live ontology import, real Google write or company-record update was performed. Test recipient, Calendar ID/
time slot and spreadsheet ID/range were requested asynchronously; none supplied at
this point. Those actual write tests remain pending operator targets and normal
action approvals. They were not replaced with fabricated receipts. New client
systems still require published knowledge and configured authorized adapters.

Memory/outcome inspection is interactive. Validated experience promotion remains
an operator backend action. Reinforcement learning and automatic ontology/rule
publication are outside this change.

## Main files

Frontend: `src/api/{client,investigations,compositions}.ts`,
`src/screens/app.index.tsx`,
`src/features/investigations/{InvestigationWorkspace,InvestigationList,DynamicInvestigationWorkspace,CompositionCanvas,CompositionPanels,CompositionOptions}.tsx`,
`composition.test.tsx`, and `e2e/dynamic-investigation.spec.ts` plus its fixture.

Backend: `workflow_api/composition_presentation.py`, `investigation_jobs.py`,
`business_ontology_routes.py`, `business_composition.py`, `client_packages.py`,
`main.py`, `live_providers.py`, `procurement.py`; `planner/provider.py`;
`runtime/{service,delegation,capability_composition,crew}.py`;
`tests/test_composition_presentation.py`, `tests/test_live_providers.py`;
`scripts/check_dynamic_investigation.py`.

User flow and reproducible commands:
`docs/simpson-business-ontology/dynamic-investigation-ui.md`.


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
