# Phase 1: shared business preparation

Implemented locally, backend only. No frontend edits, deployment, live knowledge import, new paid model tests or company writes. This phase connects existing components; it does not implement the next phase's generic agent factory, new client ontology, memory or learning.

## Reused components and audited gaps

The existing five-layer knowledge package/version store, Phase 2 intent interpreter and deterministic dependency closure, typed mappings/source query validator, evidence requirement registry and coverage providers remain authoritative. Existing scenario manifests/adapters preserve captured observations and generated event provenance. The general planner already received ontology metadata, but not the investigation preflight's actual evidence coverage. The investigation planner had its own preflight path. Registry supports current tool discovery/assignment; dynamic master-child coordination already exists in `runtime/delegation.py`; CrewAI execution stays in `runtime/crew.py`.

`SharedBusinessPreparation` now owns the previous preflight implementation; `InvestigationCoverage.preflight` delegates to this same instance. The application installs it on the general workflow service. Existing direct legacy investigation plans without preflight remain readable; new prepared plans include shared context.

## Interfaces and typed result

- `prepare(auth, body)`: existing goal/inputs/version/scenario plus optional client/domain labels and workspace/tenant assertions. Assertions must match authenticated scope. Labels are descriptive, not authority or a claim of another client's domain support. Tenant scope follows the platform's current workspace boundary.
- `get` / `checked`: load scoped hash-protected preparation; verify pinned knowledge/provider, current source bindings/metadata and scenario snapshot.
- `context`: deduplicated planner projection, with ID references to full relevant definitions and mapped source observations. Raw unrestricted fields are excluded. Required dependencies are never sampled away; oversized context is rejected explicitly.
- `BusinessEvidenceAdapter.invoke(auth, {preparation_id, task})`: freshly evaluate a prepared task using existing source/scenario retrieval, current access and coverage. No caller-supplied queries/fields/verified facts.
- `BusinessEvidenceConnector`: implements the existing graph/delegation connector protocol with `bind_context`, `reservation`, `invoke`; binds exactly to the workflow preparation. It creates no new orchestration engine or grants.

Result schema: `workflow_api/schemas/business-preparation-v1.json`. Fields include goal/outcomes, scope/domain, per-task concepts/relationships/dependencies/providers/mappings/read paths/rules/requirements, original mapped evidence, coverage/gaps, capabilities, Registry tool candidates, provenance, observation timestamps, ontology/hash/configuration/mapping/provider pins, scenario pin and source stamps. `preflight_id` is the preparation ID, preserving the previous terminal/API vocabulary and storage.

Coverage distinguishes ready, ready with limitations, needs input, insufficient evidence, conflicting evidence and unsupported. Stable coverage facts and detailed mapping requirements remain separate. Missing identifiers require input and cause no company reads. Negative authorization/exclusion/policy outcomes remain known outcomes. Unrelated downstream requirements do not block comparison.

## Planning and persistence

Investigations and general `plan_workflow` both consume the same service. General request context can include:

```json
{
  "generation_mode": "hierarchy",
  "business_request": {
    "version_id": "YOUR_SAVED_ONTOLOGY_VERSION",
    "inputs": {"identifiers": {"complaint_id": "A-2025-9-070"}},
    "client_id": "simpson",
    "domain_id": "manufacturing"
  }
}
```

Without explicit business selection, supported goals use current owned knowledge. Unrelated goals or unconfigured business knowledge retain general planning compatibility and disclose unsupported/not configured context. Explicit invalid selections fail; authorization errors are not converted into missing data.

Provider-authored preparation pins are discarded. The server pins preparation ID/hash, workspace/owner, knowledge/source versions, observations and scenario in workflow metadata. Recorded generated-workflow pins cannot be changed or removed on save. Approved runtime revisions verify their pin; adapter execution also checks current authority/metadata. Existing planner idempotency preserves the original result; historical permission is never a new source grant. Existing graph contracts, Registry assignment and approval semantics remain.

The generic planner's older definition contribution trace is retrieved against the selected version, including its pinned policy snapshots, rather than mixing a selected old ontology with new policy heads.

## Backend commands

Use an isolated application database. See `evidence-coverage.md` to prepare connected cases first. The following reuses the existing CLI and performs no paid model calls:

```bash
cd /home/raf/agentic-ai-builder
umask 077
CHECK_DIR=/tmp/simpson-evidence-coverage-20261104-01
DB="$CHECK_DIR/isolated.sqlite3"
EVIDENCE_CONTEXT=$(.venv-integrations/bin/python -c 'import json,sys; d=json.load(open(sys.argv[1])); c=next(c for c in d["cases"] if c["variant"]=="complete"); print(json.dumps({"dataset_id":d["dataset_id"],"case_id":c["case_id"]}))' "$CHECK_DIR/environment.json")
OBJECTIVE='Compare complaint A-2025-9-070 with its linked inspection.'
.venv-integrations/bin/python -B scripts/simpson_investigation.py --database "$DB" preflight \
  --objective "$OBJECTIVE" --evidence-context "$EVIDENCE_CONTEXT" > /tmp/shared-preparation.json
PREPARATION_ID=$(.venv-integrations/bin/python -c 'import json; print(json.load(open("/tmp/shared-preparation.json"))["preflight_id"])')
.venv-integrations/bin/python -B scripts/simpson_investigation.py --database "$DB" preparation --preparation-id "$PREPARATION_ID" --section concepts
.venv-integrations/bin/python -B scripts/simpson_investigation.py --database "$DB" preparation --preparation-id "$PREPARATION_ID" --section facts
.venv-integrations/bin/python -B scripts/simpson_investigation.py --database "$DB" preparation --preparation-id "$PREPARATION_ID" --section mappings
.venv-integrations/bin/python -B scripts/simpson_investigation.py --database "$DB" preparation --preparation-id "$PREPARATION_ID" --section evidence
.venv-integrations/bin/python -B scripts/simpson_investigation.py --database "$DB" preparation --preparation-id "$PREPARATION_ID" --section gaps
.venv-integrations/bin/python -B scripts/simpson_investigation.py --database "$DB" preparation --preparation-id "$PREPARATION_ID" --section capabilities
.venv-integrations/bin/python -B scripts/simpson_investigation.py --database "$DB" preparation --preparation-id "$PREPARATION_ID" --section tools
.venv-integrations/bin/python -B scripts/simpson_investigation.py --database "$DB" preparation --preparation-id "$PREPARATION_ID" --section pins
.venv-integrations/bin/python -B scripts/simpson_investigation.py --database "$DB" retrieve --preparation-id "$PREPARATION_ID" --task inspection
.venv-integrations/bin/python -B scripts/simpson_investigation.py --database "$DB" plan \
  --objective "$OBJECTIVE" --evidence-context "$EVIDENCE_CONTEXT" --request-key "shared-plan-$(date +%s)" \
  --planning-mode offline --analysis-mode offline > /tmp/shared-plan.json
WORKFLOW_ID=$(.venv-integrations/bin/python -c 'import json; print(json.load(open("/tmp/shared-plan.json"))["workflow_id"])')
.venv-integrations/bin/python -B scripts/simpson_investigation.py --database "$DB" graph --workflow-id "$WORKFLOW_ID"
.venv-integrations/bin/python -B scripts/simpson_investigation.py --database "$DB" validate --workflow-id "$WORKFLOW_ID"
```

Company-source reads require the existing configured credential references (add `--credentials-database .local/workflows.sqlite3` when appropriate). Do not copy credentials. For captured scenarios, pass `--evidence-context '{"dataset_id":"YOUR_RELEASE_ID","case_id":"YOUR_CASE_ID"}'` to preflight/plan, using real IDs from the environment listing. Original observations remain captured; supplemental events remain generated. Do not expect scenario completeness in company-source mode.

The existing HTTP `POST /business-ontology/v1/investigations/preflight` prepares requests. New `GET /business-ontology/v1/preparations/{id}` inspects them and `POST /business-ontology/v1/preparations/retrieve` invokes a task. Existing session/CSRF/origin transport applies.

General dynamic generation uses existing authenticated `POST /workflows/plan` with the usual request envelope:

```json
{
  "request_id": "shared_general_check",
  "operation": "plan_workflow",
  "idempotency_key": "shared-general-check-001",
  "payload": {
    "objective": "Compare complaint A-2025-9-070 with its linked inspection.",
    "context": {"generation_mode": "hierarchy", "business_request": {"inputs": {"identifiers": {"complaint_id": "A-2025-9-070"}}}}
  }
}
```

That endpoint uses its configured provider; unlike offline terminal planning it can incur a model call. Existing save/validate/approval operations remain required for runtime execution. This task tested this path with deterministic providers, not a paid model.

## Registering the read-only adapter

`retrieval_tool_definition()` exports a schema-valid `business_retrieve_evidence` tool (`business.retrieve_evidence`, provider `builder_business`). The app wires its connector into the existing runner when present. An operator must register/enable the tool/provider in the existing server-owned Registry policy and grant the required scopes before agents can select it; registration creates no executable assignment. No live Registry policy was changed here. Direct backend/CLI retrieval uses authenticated existing source authority. General child calls use the normal Registry exact-binding checks plus the workflow-bound adapter. Fresh agents or automatic client onboarding are Phase 2, deliberately not implemented.

## Verification

See `openspec/changes/shared-business-preparation/verification.md` for exact test counts, file inventory, terminal acceptance and limitations. Missing facts in real data remain explicit. Context/storage byte bounds and existing read/call/time controls remain; no model token/cost ceiling was introduced. No frontend or production changes.
