# Phase 2: dynamic capability composition

Implemented locally, backend only. No frontend edits, deployment, service restart, live Registry-policy changes, company writes or paid-model evaluation. Automated effects use fake model/HTTP/connector transports. This phase does not add long-term memory, learning or Phase 3 recovery.

## What now happens

A business goal goes through Phase 1 shared preparation. Registered executable capability contracts describe evidence retrieval, supported interpretation and available connector operations. The existing general planner provider can select operations from this catalogue. A deterministic compiler expands registered dependencies, matches authorized tools and builds temporary agent configurations. Registry validates the definitions; the normal workflow lifecycle assigns executable tools and approves effects. The existing master-child runtime and CrewAI adapter execute the result.

The same named permanent warranty/inspection agents are not instantiated for every goal. Configuration IDs are unique to the composition/task, and goals, schemas, ontology/evidence references and tool candidates come from the selected contracts. Model text never installs an executable operation.

Offline mode uses Phase 1's requested outcomes or explicit typed operation IDs. It is diagnostic planning, not model reasoning. Model mode reuses `service.planner.provider.generate`; it requires schema-valid `metadata.capability_requests` and respects unresolved requirements. If capability selection introduces additional supported business dependencies, shared preparation expands them through the existing canonical retrieval questions and pinned resolver. No new domain keyword interpreter was added.

## Contracts, planning and tool matching

`workflow_api/schemas/capability-contract-v1.json` describes capability ID/operation/purpose, input/output schema, ontology/fact requirements, preconditions, tool operations, effects, verification, completion criteria and domain scope. `capability_contracts.py` registers current business outcomes as configuration. External operation contracts are admitted only for known semantics backed by an actual visible registered tool definition.

The prepared task DAG is bounded, deterministic after selection and cycle-checked. Independent reads can run in parallel; comparison/review/report tasks require their declared predecessors. Coverage-based conditions select interpretation versus a backend needs-evidence branch. A blocked conclusion can still yield a completed report. Missing resource inputs or unsupported tools block workflow generation and remain structured preparation gaps.

Matching proves input/output compatibility using existing Registry helpers, checks the exact registered operation/tool, current scopes/permissions/policy, connector presence, side effects and explicit resource inputs. A selected Google connection is checked for ownership, connection state and operation scopes using the existing account binding. Source operations retain Phase 1's query validator and authority. No arbitrary SQL or generated field paths are executable.

Calendar IDs, engineer references, recipients, Sheets resources/ranges and other required inputs are not inferred from a tool's presence. In model mode, proposed external operation inputs must be bound to explicit `resources.operation_inputs` or explicit request `operations`; invented model values are discarded and the missing inputs remain. Engineer references are explicit user task context, not proof of company assignment/approval. Calendar events do not establish inspection completion; draft receipts do not establish email delivery.

## Agent factory and persistence

`AgentConfigurationFactory` creates existing canonical Registry agent definitions with workflow/task/parent references, role/goal, schemas, relevant ontology/evidence references, required facts, candidate tools, completion/verification rules, run-only memory scope and current reviewed execution limits. Configurations and task plans persist in owner/workspace-scoped hash-protected `business_compositions` records. `permitted_tools` is empty at proposal time: actual grants come only from normal Registry assignment and current authorization.

One master coordinates read/analysis/report children. External write/draft operations are deterministic tool nodes after the master, each behind the existing exact-action approval gate, rather than autonomous write agents. These action definitions have no model calls. No recursively spawned agent definitions are allowed. Repeated workflow generation reuses identical registered definitions and bindings without invalidating grants.

Generated workflow nodes use the unchanged canonical graph and dynamic delegation contracts. Definitions are validated using existing Registry registration/policy. The compiled control metadata, agent definitions, tools, graph, budgets and approval gates cannot be silently changed or removed on save or approved runtime load; regenerate a composition to change its execution contract. Historical noncomposition workflows remain compatible.

## Runtime context and result verification

`runtime/capability_composition.py` supplies guards to `DelegationSession`; it is not a scheduler or another execution engine. The existing runtime still owns concurrency, persistence, attempts, leases, budgets and tool dispatch.

The master sees ready registered children, task dependencies, completed result summaries, errors/pending work and resources. Each child receives its assigned task, relevant pinned ontology, mapped source evidence and actual completed dependencies. Raw stored envelopes are kept separately from the model's evidence packet. A child cannot replace context or choose a different prepared task/resource. Duplicate or premature delegation and premature final synthesis fail explicitly.

Retrieval must actually call the assigned tool before claiming completion. Schema-valid returned observations and deterministic coverage are preserved as backend evidence. Analysis uses existing citation validation; unsupported business conclusions remain unverified interpretations. Required facts unavailable at runtime suppress the dependent model analysis and produce a backend evidence requirement. Final task results come from collected runtime outputs, not a master-invented list. Master narrative remains an interpretation.

External actions retain normal Registry/action approvals and existing connector resource restrictions/effect journals. Required provider IDs, cancellation status and echoed resource identity are checked; a malformed/failed/wrong-resource receipt cannot establish success. Execution traces retain actual calls and invocation/configuration IDs. Source policy applicability, recommendation, commercial authorization and official approval remain separate.

## Backend interfaces

- `POST /business-ontology/v1/compositions`: prepare and persist a composition; defaults to configured model planning.
- `GET /business-ontology/v1/compositions/{id}`: inspect scoped contracts/tasks/configurations/gaps.
- `POST /business-ontology/v1/compositions/{id}/workflow`: compile a validated draft; no execution or external effects.
- Existing `POST /workflows/plan` with `context.composition_id`: produce the same compiled draft for the normal save/validate/approve/execute lifecycle. Its objective must match the saved composition.

Existing authenticated session/origin transport applies. This phase does not change the UI to submit those new requests automatically.

Example configured-model preparation body, using a real saved Phase 1 ID:

```json
{
  "objective": "Compare complaint A-2025-9-070 with its linked inspection.",
  "request_key": "comparison-compose-unique-001",
  "preparation_id": "YOUR_OWNED_PREFLIGHT_ID",
  "planning_mode": "model"
}
```

For external actions, select actual enabled tool-derived IDs from the returned catalogue (for example `tool.extension_mail_draft`, when installed), and supply exact inputs and operator-reviewed destination. Unregistered/unavailable operations return explicit gaps. A natural-language resource mention alone is not sufficient for an automatically generated external write in this phase; typed confirmation is required.

## Exact terminal checks — offline, read-only diagnostic Registry

The new CLI reuses `simpson_investigation.build` and shared preparation. Its deliberately restricted local operator Registry enables only the read-only business evidence adapter. It does not change live Registry policy or approve/execute workflows. It refuses the known live application database path. HTTP model/operational acceptance is separate.

The prior private scenario environment must exist; otherwise prepare a fresh isolated dataset using `evidence-coverage.md`.

```bash
cd /home/raf/agentic-ai-builder
umask 077
PY=.venv-integrations/bin/python
CHECK_DIR=/tmp/simpson-evidence-coverage-20261104-01
DB="$CHECK_DIR/isolated.sqlite3"
OUT=$(mktemp -d /tmp/capability-manual-XXXXXXXX)
EVIDENCE_CONTEXT=$("$PY" -c 'import json,sys; d=json.load(open(sys.argv[1])); c=next(c for c in d["cases"] if c["variant"]=="complete" and c["source_identifiers"]["complaint_id"]=="A-2025-9-070"); print(json.dumps({"dataset_id":d["dataset_id"],"case_id":c["case_id"]}))' "$CHECK_DIR/environment.json")

"$PY" -B scripts/capability_composition.py --database "$DB" prepare \
  --objective 'Compare complaint A-2025-9-070 with its linked inspection.' \
  --evidence-context "$EVIDENCE_CONTEXT" \
  --request-key "compose-$(date +%s%N)" > "$OUT/composition.json"
COMPOSITION_ID=$("$PY" -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["composition_id"])' "$OUT/composition.json")

"$PY" -B scripts/capability_composition.py --database "$DB" inspect --composition-id "$COMPOSITION_ID" --section tasks
"$PY" -B scripts/capability_composition.py --database "$DB" inspect --composition-id "$COMPOSITION_ID" --section configurations
"$PY" -B scripts/capability_composition.py --database "$DB" inspect --composition-id "$COMPOSITION_ID" --section contracts
"$PY" -B scripts/capability_composition.py --database "$DB" inspect --composition-id "$COMPOSITION_ID" --section selected_tools
"$PY" -B scripts/capability_composition.py --database "$DB" workflow --composition-id "$COMPOSITION_ID" > "$OUT/workflow.json"
"$PY" -B scripts/capability_composition.py --database "$DB" validate --composition-id "$COMPOSITION_ID"
```

Expected: ready composition; two read specialists (complaint and linked inspection), comparison specialist, report specialist, one coordinating master; dependencies connecting reads to comparison and report; actual source/policy/configuration pins and no executable tool grants in the proposed definitions. Validation returns `valid: true`. No model call occurred in this CLI path.

For a different arrangement, replace the objective with `Check warranty readiness for complaint A-2025-9-070.` and a fresh request key. Expect warranty evidence/interpretation, without a comparison specialist. Complete scenarios supply configured supplemental facts; company-only mode can correctly produce a needs-evidence branch. History is supported by existing company-source retrieval, but the prior complete scenario release only declares comparison/warranty/replacement completeness.

Check unsupported operation handling without any action:

```bash
"$PY" -B scripts/capability_composition.py --database "$DB" prepare \
  --objective 'Approve every warranty claim.' \
  --request-key "unsupported-$(date +%s%N)" \
  --operations '[{"capability_id":"unregistered.claim_approval","inputs":{}}]'
```

Expected: unsupported capability gaps, no generated executable specialist/action and no external effect.

Run actual composed runtime/CrewAI checks with fake transports:

```bash
PYTHONDONTWRITEBYTECODE=1 "$PY" -B -m pytest -q -p no:cacheprovider tests/test_business_composition.py
```

## Limits and next phase

The current registered business operations and known connector semantics are supported, not arbitrary new business logic. A new client requires its own approved concepts/mappings/evidence contracts and any missing executable capability adapters. Multiple different resource sets for the same capability in one composition are deliberately rejected as ambiguous; use separate prepared operations/workflows. Missing inputs are resolved by a new immutable preparation with a new request key, not fabricated or automatically filled. Existing reviewed execution limits may reject a plan whose depth cannot fit the master budget; no permission/budget is increased by model output.

No new model token/cost ceiling was added; existing runtime policy and opt-out remain. External operations require actual registered/enabled connectors and existing approval/resource policy. The diagnostic CLI cannot provision production connectors. No live Google/model-quality acceptance, UI integration, deployment, long-term memory, reinforcement learning or Phase 3 recovery is claimed. Full verification and file inventory: `openspec/changes/dynamic-capability-composition/verification.md`.
