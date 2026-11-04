# Interactive dynamic business investigations

The existing Business investigations screen now supports the shared preparation,
dynamic capability composition and scoped memory/recovery phases. Historical
investigations retain their existing URLs and execution history. The shared
workflow/agent/tool v1 contracts remain the execution authority.

## User flow

1. Enter a supported business goal on the existing overview page. For example:
   `Compare complaint A-2022-12-013 with its linked inspection. Prepare a
   source-backed report identifying agreements, discrepancies and missing
   inspection evidence. Do not assess warranty or perform operational actions.`
2. Optionally select an authorized Google connection, registered action and its
   explicit input fields, or an already published client knowledge package.
   The interface does not guess recipients, spreadsheet ranges or calendars.
3. Generate the workflow. A durable background job selects registered
   capabilities; application code closes dependencies and creates registered
   task-specific agent configurations and the canonical draft. Generation does
   not execute a workflow or authorize an external action.
4. Inspect the task graph and click a node for its results, dependencies,
   evidence requirements and tools. Independent tasks have parallel dependency
   paths. Status is read from persisted runtime checkpoints, not animated success.
5. Validate, approve and run using the existing workflow lifecycle. External
   actions require their actual runtime approval gate, separately from workflow
   approval. The pending action details show prepared resources before a decision.
6. Inspect the report, cited mapped records, observations and remaining evidence
   requirements. A completed comparison can legitimately report missing facts.
   Missing policy/identity/authorization facts are not synthesized as company truth.
7. Use **Ontology evidence**, **Agents & tools** or **Memory & recovery** for
   optional context inspection. Detailed mappings and version pins are collapsed.
8. Resume eligible failed work explicitly, or update the request to prepare a new
   immutable composition. Recovery eligibility is rechecked by the backend.
   Uncertain external effects require reconciliation; the UI does not replay them.

The existing three-dot rename/delete controls work for both new and historical
investigations. Names change display metadata; objectives and evidence pins stay
immutable. Delete is confirmed, blocked for active runs, and preserves history.
A deleted canonical workflow cannot be executed using an older approved revision.

## API integration

- `GET /session`: `dynamic_composition_available` advertises this integration.
  Older servers without it keep the historical prompt path.
- `POST /business-ontology/v1/investigations/jobs`: `compose` and `recover` reuse
  durable jobs. Polling never starts paid work. Interrupted paid jobs are not
  automatically replayed.
- `GET /business-ontology/v1/compositions`: owner-scoped list.
- `GET /business-ontology/v1/compositions/{id}/view?run_id=...`: saved tasks,
  scoped results, pins, approval availability, usage, outcome and recovery view.
- `PUT /business-ontology/v1/compositions/{id}/display-name`.
- `DELETE /business-ontology/v1/compositions/{id}` with `{"confirmed":true}`.
- `POST /business-ontology/v1/compositions/{id}/runs/{run}/cancel`.
- `GET /business-ontology/v1/client-packages`: published, owner-scoped packages.

Normal canonical save/validate/approve/execute/decide-approval operations retain
permission, revision, idempotency and Registry enforcement. Historical inspection
can display saved pins after metadata changes; that does not permit stale execution.
The view omits raw source envelopes, credentials and archived recovery evidence.

## Live integration corrections

The configured launcher now registers the mapped business read adapter and keeps
it when installing Google adapters. It uses the configured model for generated
agents. A dedicated strict model selector returns registered capability IDs and
unsupported requirements; application code generates the graph. The procurement
planner decorator forwards this protocol instead of forcing a second full graph
proposal. Missing source evidence belongs in report findings, not in the selector's
unsupported-capability list. The delegation proposal schema exposes only the
assigned task ID; runtime-owned context is injected by code and cannot be supplied
by the model.

These corrections are generic to registered capabilities. They do not add
complaint-specific graph templates or grant tools based on model suggestions.

## Local checks

From the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
  tests/test_composition_presentation.py tests/test_business_composition.py \
  tests/test_agent_memory_recovery.py tests/test_investigation_jobs.py \
  tests/test_live_providers.py tests/test_planner.py tests/test_runtime.py tests/test_workflow_api.py
.venv-integrations/bin/python -B scripts/validate_contracts.py
.venv-integrations/bin/python -B scripts/generate_ui_contracts.py --check
openspec validate dynamic-investigation-ui --strict
```

From `frontend`:

```bash
npm run typecheck
npm run lint
npm test
npm run build
npx playwright test e2e/dynamic-investigation.spec.ts \
  e2e/investigation-workflow.spec.ts e2e/investigation-actions.spec.ts
```

Browser tests use isolated fake providers and the existing configured test login
secret. They cover desktop/mobile, branches, approval, report/citation navigation,
refresh, missing inputs, explicit recovery, failed planning and exact-action gates.
They do not send Google messages or create Calendar/Sheets data.

## Configured-provider acceptance

```bash
# Source reads/preparation; no model calls or company writes.
.venv-integrations/bin/python -B scripts/check_dynamic_investigation.py \
  --database .local/workflows.sqlite3

# Paid configured-model execution. Run only with authorization for the selected
# complaint and mapped evidence to the configured API endpoint.
.venv-integrations/bin/python -B scripts/check_dynamic_investigation.py \
  --database .local/workflows.sqlite3 --live-model
```

The acceptance script copies the application database to a private directory under
`.local/dynamic-investigation-checks/`, disables existing copied jobs, uses an
isolated registry, allows only mapped read/compare/report capabilities, and writes
private snapshots/receipts there. It never changes original company records,
production workflow state, the live registry file or external business systems.
Do not commit the private copied databases, views or OAuth material.

## Limits and deployment

This UI exposes the three existing backend phases; it does not implement arbitrary
new tools, autonomous permission changes, reinforcement learning, automatic
ontology publication or automatic onboarding of previously unknown client systems.
Memory/outcome inspection is available; experience validation/promotion remains
an operator backend operation. Actual Google write acceptance needs explicit test
recipient, Calendar/time slot and spreadsheet/range, plus normal permissions and
action approval. Scoped read checks do not prove those writes work.

Local implementation/build/browser verification is separate from a website
rollout. Final acceptance details and deployment status are recorded in
`openspec/changes/dynamic-investigation-ui/verification.md`.

The configured-model pilot also verified the existing server-owned usage opt-out:
when `BUILDER_ENFORCE_USAGE_BUDGETS=0`, the configured model bridge uses provider
capacity and settlement accepts actual token/cost usage above placeholder
reservations. Enabled budgets retain enforcement. Model call, tool call and time
controls remain finite. This does not remove provider context/output limits.
Citation schemas are narrowed per evidence packet; invalid record/field pairs are
still rejected independently after model output validation.


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
