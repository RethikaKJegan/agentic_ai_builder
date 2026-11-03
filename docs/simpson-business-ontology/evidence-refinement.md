# Backend evidence refinement

Implemented and tested backend only, then deployed after the user's explicit approval with the report-schema fix. Live knowledge is revision 8; backend/worker restarted, frontend unchanged, original versions/runs preserved and company records unchanged. See [rollout verification](../../openspec/changes/investigation-report-schema/verification.md). Generate fresh UI plans; the commands below remain available for isolated backend checks.

## Retrieval and conversion

The explicit authoring package is revision 2 with 47 mappings. Existing three structured readiness rules remain unchanged. New source-scoped native reference contracts resolve:

- `tickets.complaintRecord.natureOfCustomerComplaint` → `simpsoncodes._id`, returning original identifier, business code, description, type, active observation and source references.
- `tickets.serviceEngineer` → `users._id`, projecting only name/active and native identity. Resolution does not establish an engineer role, approval authority or active status beyond the recorded observation.
- `tickettimelines.ticketId` → `tickets._id`, returning bounded stage, description and creation-time observations. A timeline observation is not automatically a verified state transition; closure rationale requires the supported closure stage plus recorded description.
- Ticket `engineNo` → invoice `engineSerialNumber` as an explicit **candidate** read path. All bounded candidates and available company/list observations remain separate. No serial equality, model/company agreement or unique candidate creates physical identity or policy applicability.

The controlled-code relationship uses the actual stored native reference, commonly a UUID. The code such as `UC22` comes from the referenced record; it is not substituted into the original complaint field. Unknown codes remain unresolved. No description is generated. The executor and resolution view are driven by saved bindings and record identifiers, not particular prompts or complaint IDs.

Date conversion belongs to each saved mapping:

| Mapping | Accepted values | Meaning and behavior |
| --- | --- | --- |
| Inspection failure date | Native date/datetime, strict ISO calendar date, explicit `DD-MM-YYYY` | Reported failure calendar day; no fallback to registration or inspection date |
| Inspection date | Native date/datetime, ISO calendar date or ISO timestamp calendar component | Recorded inspection calendar day; preserve its calendar component without assigning an unstated timezone |
| Existing sale/invoice dates | Existing registered ISO/native-date conversion | No global day/month reinterpretation |

Invalid dates remain invalid; unsupported slash forms such as `03/04/2026` are ambiguous. Null remains unknown and zero/false retain their values. Raw source fields are retained, and the two refined date mappings also expose raw value, conversion, precision, event meaning and timezone-inference flag. An explicit field format interprets `03-04-2026` as 3 April only for the declared DMY field.

Auxiliary lookup projections live in `retrieval-mappings.json`, merged into the immutable import catalogue. The existing `source-mappings.json` and saved-graph collection inventory are unchanged. Current unavailable sampled mappings remain `enginedetails.buildDate` and `enginedetails.engineModel`; this is not proof of database-wide absence.

Work-order `complaintReferenceNumber` exists in the supplied model, but it is not a declared typed ticket reference (the model's proposed ticket reference is commented out). This refinement does not invent that join. Additional work-order, service-history document, checklist/attachment, verified diagnosis and authority providers need separately supported contracts. Available supported history is retrieved from complaint, invoice, QA and timeline records.

## Requirements, gaps and reports

`workflow_api/business_evidence.py` is the reusable pure registry/evaluator. Each requirement defines fact ID, task, business meaning, level, provider, validation rule, unknown behavior and registered advisory recovery action. Levels are execute, business conclusion, optional support and downstream. Pinned policy coverage mode determines sale/invoice date requirements; selecting a policy never establishes applicability or authority.

Supported checklists cover complaints, comparison, warranty readiness, replacement evidence, history and effectiveness evidence readiness. The latter adds only a retrieval capability and reuses the existing report agent; no agent or operational monitoring scheduler is added. A supported terminal objective is `Review corrective-action effectiveness evidence for engine SERIAL and prepare a report.` Population metrics and operational actions remain unsupported.

Inspection completion is downstream evidence for a comparison and does not block reading/comparing a linked report. Warranty, authorization and incorporation are not introduced into comparison/history requirements by model prose. Required source observations, unverified diagnoses, selected policy, physical identity and actual commercial authorization retain separate meanings. Production evidence evaluation accepts no caller-supplied verified fact override.

Structured gaps expose `fact_id`, `task`, `requirement_level`, `state`, `reason`, `impact`, `recovery_action`, source references, context ID and stable gap ID. States distinguish not retrieved/found, invalid, ambiguous, unsupported mapping and not established. Permission failures retain the existing denied API response and never become a successful empty read. Deduplication is by task/fact/record/level/state and merges provenance; different records remain distinct.

Reports preserve existing frontend-compatible fields and add task evidence, grouped gaps, downstream requirements, resolved references, recovery actions and requirement hash. Main missing information comes from registered facts. Original agent suggestions remain in `run.outputs`; report copies remove repeated suggestion lists and disclose reconciliation counts. An agent cannot create a mandatory requirement. Model discrepancy claims remain unverified comparisons/additional observations, with citations; they do not prove contradiction or causality. Confirmed business findings remain empty until a trusted provider can establish them.

Recovery actions are advisory (`executable:false`), not new write tools. They identify permitted retrieval/knowledge inspection or fresh typed plan inputs. Supply `assessment_date` and a pinned `policy_id` in a new plan; do not overwrite a completed run. Existing authority, source stamps, bounds and version checks remain enforced. Requirement-registry changes are included in the investigation catalogue fingerprint, requiring fresh plans rather than silently changing existing execution semantics.

## Isolated scenarios

Agent packets merge compatible observations with all references and preserve conflicting observations separately. Optional timeline context is limited to three records with explicit included/omitted counts; required evidence is never sampled by this rule. Full bounded results remain persisted. Nine local fixture-provider turns through the actual CrewAI adapter passed within the existing budget; this is not a real-model reasoning evaluation.

`scripts/check_evidence_scenarios.py` writes twelve explicit generated scenarios: complete/incomplete/ambiguous evidence for comparison, warranty, replacement and effectiveness. Sign-off, authorization, return receipt, QA/incorporation and related lifecycle events are case-scoped and temporally ordered. Generated provenance is mandatory, and foreign context or invalid timelines fail.

Scenario evaluation is separate from production evaluation. Even a complete scenario cannot establish a live warranty approval or business conclusion. No HTTP/normal investigation input accepts scenario fact overrides. Generated records never enter live Simpson results or the company database.

```bash
cd /home/raf/agentic-ai-builder
SCENARIO_ROOT=$(mktemp -d /tmp/simpson-scenarios-XXXXXXXX)
.venv-integrations/bin/python scripts/check_evidence_scenarios.py \
  --directory "$SCENARIO_ROOT/check"
```

## Exact backend testing commands

Create a fresh private isolated store and run independent bounded source checks. This deliberately performs no model calls and does not import into the live app:

```bash
cd /home/raf/agentic-ai-builder
EVIDENCE_ROOT=$(mktemp -d /tmp/simpson-evidence-XXXXXXXX)
EVIDENCE_DIR="$EVIDENCE_ROOT/check"
.venv-integrations/bin/python scripts/check_evidence_refinement.py \
  --database .local/workflows.sqlite3 --directory "$EVIDENCE_DIR" \
  --complaint-id I-2026-3-068 \
  --complaint-id A-2025-9-070 \
  --complaint-id A-2022-12-013
```

Expected: `passed:true`, twelve checks, compilation passed, unchanged original knowledge, zero company/live-application writes and zero model calls. Company evidence is saved only in the private output directory. Existing source credentials are borrowed in memory, never copied.

Submit a new question and inspect its requirements and retrieval bindings:

```bash
.venv-integrations/bin/python scripts/simpson_investigation.py \
  --database "$EVIDENCE_DIR/isolated.sqlite3" \
  --credentials-database .local/workflows.sqlite3 \
  plan --objective 'Compare complaint I-2026-3-068 with its linked inspection and prepare a source-backed report.' \
  --request-key terminal-refinement-plan-001 \
  --planning-mode offline --analysis-mode offline \
  > "$EVIDENCE_DIR/manual-plan.json"

WORKFLOW_ID=$(.venv-integrations/bin/python -c \
  'import json,sys; print(json.load(open(sys.argv[1]))["workflow_id"])' \
  "$EVIDENCE_DIR/manual-plan.json")

.venv-integrations/bin/python scripts/simpson_investigation.py \
  --database "$EVIDENCE_DIR/isolated.sqlite3" \
  requirements --workflow-id "$WORKFLOW_ID"
```

The saved plan's `ontology_context.tasks` contains the task requirements, selected mappings and dependencies. For the full executable Phase 2 read plan:

```bash
.venv-integrations/bin/python scripts/ontology_retrieval.py \
  --database "$EVIDENCE_DIR/isolated.sqlite3" \
  --credentials-database .local/workflows.sqlite3 \
  preview --question 'Show inspection findings for complaint I-2026-3-068.' \
  --request-key terminal-refinement-preview-001
```

Execute the saved investigation:

```bash
.venv-integrations/bin/python scripts/simpson_investigation.py \
  --database "$EVIDENCE_DIR/isolated.sqlite3" \
  --credentials-database .local/workflows.sqlite3 \
  run --workflow-id "$WORKFLOW_ID" --request-key terminal-refinement-run-001 \
  > "$EVIDENCE_DIR/manual-created.json"

RUN_ID=$(.venv-integrations/bin/python -c \
  'import json,sys; print(json.load(open(sys.argv[1]))["run_id"])' \
  "$EVIDENCE_DIR/manual-created.json")

.venv-integrations/bin/python scripts/simpson_investigation.py \
  --database "$EVIDENCE_DIR/isolated.sqlite3" \
  --credentials-database .local/workflows.sqlite3 \
  execute --run-id "$RUN_ID" > "$EVIDENCE_DIR/manual-executed.json"
```

Inspect each section; change `resolutions` to `dates`, `associations`, `requirements`, `gaps`, `recovery`, `findings` or `all`:

```bash
.venv-integrations/bin/python scripts/simpson_investigation.py \
  --database "$EVIDENCE_DIR/isolated.sqlite3" \
  report --run-id "$RUN_ID" --section resolutions
```

`offline` is an explicit deterministic diagnostic, not CrewAI/model reasoning. Configured model planning and CrewAI remain available with `--planning-mode model --analysis-mode crewai`; those modes send selected mapped evidence to the configured model endpoint. No new paid model evaluation was performed for this refinement.

Existing HTTP preview, inspect, execute, capabilities and plan/run/report payloads expose the same new fields. No frontend is needed. Existing stored evidence does not acquire new mappings or normalized gaps automatically; use fresh isolated knowledge and fresh requests.

## Verification and remaining work

See [verification](../../openspec/changes/task-evidence-refinement/verification.md) for exact automated results, independent source checks, file inventory and limits. Authoritative policy applicability, verified physical identity, diagnosis, commercial authorization, incorporation, complete populations and exposure remain unavailable to these providers. They are not manufactured. Frontend changes, deployment, live ontology import, operational actions, new agents, full monitoring and reinforcement learning are intentionally deferred.
