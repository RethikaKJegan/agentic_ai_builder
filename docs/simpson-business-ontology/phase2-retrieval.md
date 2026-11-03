# Phase 2 — intelligent ontology retrieval

Implemented in the backend. A question now follows this path:

`question → constrained intent → saved concepts → dependency/fact closure → saved field mappings → metadata-validated read plan → authorized source reads → evidence`

This supports a bounded Simpson retrieval vocabulary. Arbitrary prompts do not gain arbitrary query or action authority. No frontend, CrewAI execution, warranty approval, replacement authorization or company writes were added.

## What works

| Request family | Examples | Result |
| --- | --- | --- |
| Complaints | `Show complaints for engine E123.`; `Find service issues for motor E123.` | Exact reported serial lookup, separate complaint/ticket hour observations, source-qualified records |
| Complaint investigation | `Show inspection findings for complaint C123.` | Complaint and exactly referenced inspection reports; unrelated and orphan reports excluded |
| Comparison | `Compare this complaint with its joint inspection.` plus explicit complaint ID | Both reported accounts, reference evidence and status semantics; no invented diagnosis |
| Bounded text search | `Find previous cooling-related breakdown reports.` | Literal `cool` substring search over the first bounded complaint sample, not a diagnosis classifier or exhaustive historical search |
| Numeric hours | `Show complaints over 100 hours.` | Registered conversion of complaint-reported hours, then numeric comparison; invalid hours reported |
| Status | `Show PUBLISHED inspection reports for engine E123.` | Exact status filter combined with the saved complaint reference, not an unrelated report scan |
| Warranty evidence | `Check warranty for engine E123.` | Readiness inputs, pinned policies, conditional date requirements and missing evidence; no coverage approval |
| Replacement evidence | `Show replacement evidence for complaint C123.` | Saved complaint references to replacement/part/dispatch/report records and missing authorization facts |
| History | `Show history for engine E123.` | Independent complaint, invoice and QA reads; cross-source serial matches remain candidate associations |
| Recurrence evidence | `Check recurrence evidence for engine E123.` | Available invoice/QA observations and explicit missing incorporation, mechanism, identity and exposure facts |

`E123` and `C123` are illustrative identifiers. They are not inserted into any source. Supply a real identifier from your data or use the reproducible live-sample commands below. Alphabetic or otherwise unclear identifiers can be passed through `--inputs '{"serial":"YOUR-SERIAL"}'` instead of inferred from prose.

## Terminal: test the complete flow

Run from the repository. This creates a **fresh isolated store** and performs bounded, read-only checks against existing configured Simpson connections. Choose a new directory if the name already exists. It preserves the Phase 1 integration store and live application knowledge.

```bash
cd /home/raf/agentic-ai-builder
RETRIEVAL_DIR=$(mktemp -u /tmp/simpson-phase2-check-XXXXXXXX)
.venv-integrations/bin/python scripts/check_business_retrieval.py \
  --database .local/workflows.sqlite3 \
  --directory "$RETRIEVAL_DIR" --live-sources
```

Expected: `passed: true`, original knowledge unchanged, zero company/live-application writes, zero copied credentials and zero model calls. The checks independently query expected IDs, then compare the resolver's actual IDs. They cover a real complaint and inspection, serial complaint lookup, and history across the service/quality databases where a QA sample exists. These are bounded observations, not complete database coverage.

Now enter a question. This example reuses the real linked complaint discovered by the check, so you do not need to guess an ID:

```bash
RETRIEVAL_QUESTION=$(.venv-integrations/bin/python -c \
  'import json,sys; print(json.load(open(sys.argv[1]))["question"])' \
  "$RETRIEVAL_DIR/linked_inspection-preview.json")

.venv-integrations/bin/python scripts/ontology_retrieval.py \
  --database "$RETRIEVAL_DIR/isolated.sqlite3" \
  --credentials-database .local/workflows.sqlite3 \
  preview --question "$RETRIEVAL_QUESTION" --request-key terminal-inspection-001 \
  > "$RETRIEVAL_DIR/preview.json"

.venv-integrations/bin/python -m json.tool "$RETRIEVAL_DIR/preview.json"
```

Preview reads only saved definitions and current saved metadata. Inspect `intent`, `concepts`, `fact_providers`, `dependency_resolution`, `mappings`, `steps`, `missing`, `version_id`, `knowledge_sha256` and `ready`. Each mapping names the exact role, collection, field, type, conversion, unit and provenance. `company_reads` is zero. Missing business facts can coexist with a safe evidence-read plan; `ready` means the **read plan** is executable, not that warranty/inspection evidence is sufficient.

Execute the saved server-owned plan and inspect it:

```bash
RETRIEVAL_ID=$(.venv-integrations/bin/python -c \
  'import json,sys; print(json.load(open(sys.argv[1]))["request_id"])' \
  "$RETRIEVAL_DIR/preview.json")

.venv-integrations/bin/python scripts/ontology_retrieval.py \
  --database "$RETRIEVAL_DIR/isolated.sqlite3" \
  --credentials-database .local/workflows.sqlite3 \
  execute --request-id "$RETRIEVAL_ID" \
  > "$RETRIEVAL_DIR/evidence.json"

.venv-integrations/bin/python -m json.tool "$RETRIEVAL_DIR/evidence.json"

.venv-integrations/bin/python scripts/ontology_retrieval.py \
  --database "$RETRIEVAL_DIR/isolated.sqlite3" \
  --credentials-database .local/workflows.sqlite3 \
  inspect --request-id "$RETRIEVAL_ID"
```

Expected: the selected complaint and linked report(s), with native source IDs and reference edges. Inspection evidence is `incomplete` because a published report does not establish actual inspection completion. That is an explicit knowledge gap, not a failed database query.

Use a new request key for each changed question/input/version. Repeating the same key/body keeps its original plan and ontology version. Repeated execution returns saved evidence after rechecking current authority/source stamps. A first execution expires after one hour; create a new request for fresh data. Request IDs are scoped to workspace and owner.

Other examples, using the same global arguments before `preview`:

```bash
preview --question 'Find service issues for motor E123.' --request-key motor-lookup-001
preview --question 'Show complaints over 100 hours.' --request-key reported-hours-001
preview --question 'Find previous cooling-related breakdown reports.' --request-key cooling-search-001
preview --question 'Compare this complaint with its joint inspection.' \
  --inputs '{"complaint_id":"C123"}' --request-key compare-report-001
preview --question 'Check warranty for engine E123.' \
  --inputs '{"assessment_date":"2026-11-03"}' --request-key warranty-inputs-001
preview --question 'Show history for engine E123 including model and build date.' --request-key missing-fields-001
```

These are CLI subcommand examples; prepend the executable/script and global database arguments from the full commands above. On this saved Simpson metadata, the final example explicitly reports unavailable `enginedetails.engineModel` and `enginedetails.buildDate` mappings. It does not substitute another model/date field.

For metadata-only previews without source access, omit `--credentials-database`. Do not use such a plan for execution: supplying credentials later changes its source stamp, so create a fresh preview with the same credential-source arguments you will use to execute. Credentials are borrowed in memory from an owner-scoped read-only SQLite connection and never copied into the isolated store. The terminal tool refuses to use the live application database as its output store.

Optional AI interpretation uses the existing configured Responses model and is explicit:

```bash
.venv-integrations/bin/python scripts/ontology_retrieval.py \
  --database "$RETRIEVAL_DIR/isolated.sqlite3" \
  preview --question 'Find service issues for motor E123.' \
  --request-key model-interpretation-001 --use-ai
```

The bounded model catalogue contains saved concept definitions, not retrieved company records. Recognized identifiers are replaced with placeholders before the call. Output has a strict schema and candidate-ID/task allowlists; field names, source references and joins cannot be supplied. Invalid output, unavailable configuration or provider failures produce a visible deterministic fallback. The model cannot override deterministic write/ambiguity/filter restrictions. Model requests disable response storage and retries. No embeddings or additional paid-service dependency were added.

## HTTP interface

Existing session, origin, workspace and owner controls apply. Responses use the normal API envelope; company data responses use `Cache-Control: no-store`.

- `POST /business-ontology/v1/retrieval/preview`: `{ "question": "Show complaints for engine E123.", "request_key": "lookup-engine-001", "inputs": {}, "use_ai": false }`; optional `version_id`.
- `POST /business-ontology/v1/retrieval/{request_id}/execute`: `{}` only.
- `GET /business-ontology/v1/retrieval/{request_id}`: original plan plus saved evidence if executed.

Do not post an edited plan. Only the scoped saved request ID is execution authority. Preview/inspection require existing read permissions; persisting retrieval diagnostics does not authorize any operational write. Source ownership and current permissions are checked again during execution and before storing evidence.

## How it is implemented

The task capability registry selects **saved mapping IDs**, never raw guessed fields or a prebuilt business workflow. A per-request scoped concept index ranks labels, aliases, definitions, attributes, predicates and modules. The deterministic interpreter supports the request families above; optional constrained AI can select valid concepts/tasks. The fact-provider registry distinguishes mappings, derived checks, pinned policies, explicit inputs and unavailable evidence.

Dependency expansion reaches a fixed point through concepts, ancestors, declared dependency relationships, mappings, rule inputs and newly required concepts. Cycle detection prevents loops. Registered predicates interpret the saved sale/invoice-date conditions. An unknown condition keeps its requirements visible; an unsupported predicate or context overflow blocks execution. Missing required knowledge is never silently trimmed.

Source projections come from saved mappings and declared native-reference bindings. Exact filters use the existing `QueryReader.objects` implementation. Dotted Mongo projections are budgeted as their selected scalar values while retaining native rows for reference traversal. Typed equality preserves ObjectId versus string distinctions. Numeric/string hours are converted by Phase 1's registered converter, never compared lexically. Conversion issues and missing observations remain explicit.

The planner's existing `business_ontology_retrieval` contract is preserved. A new server-owned `ontology_retrieval` context supplies grounded meanings, dependencies, mapping decisions and proposed reads. Its exact dataset IDs are fed into the existing KG metadata candidate pool through a trusted method argument. Every ID still passes the owned metadata index. Required schemas cannot be silently omitted to meet the 70 KB pool budget; explicit selections that omit required datasets are rejected. Existing four-source workflow execution limits remain in place. This integration supplies context; it does not execute a workflow or grant new joins.

The request table `business_retrieval_requests` stores original question, pinned version/hash, source stamps, canonical plan hash, intent and subsequent evidence. Saved authoring definitions are not reread at request time. Historical versions remain readable; versions predating the Phase 1 extension cannot generate Phase 2 reads. A changed source binding, metadata revision, credential stamp, owner or current authority invalidates execution. Supported policy selection must name a revision pinned in that version; selection does not prove applicability.

## Evidence and limits

Evidence contains the version/hash and plan hash, selected concepts/mappings, fact providers, dependencies, rules/readiness results, pinned policy references, temporal definitions, executed-step outcomes, source-qualified records, native IDs, field conversions, findings, direct-reference edges, candidate associations, missing facts and limits. Reported symptoms and potential causes remain reported observations. Readiness rules retain their saved provenance and cannot issue an official-policy decision.

`completeness` distinguishes `incomplete`, `bounded_search` and `complete_for_scoped_reads`. `record_reads_complete` describes source reads, separately from business evidence. Population scope is explicitly source records matching saved filters, never an inferred physical-engine cohort. An empty exact lookup can be complete for that scoped lookup. Invalid hours, missing requirements, truncation and unresolved cross-source identity prevent complete-evidence claims.

Each source step returns at most 20 records, using a 21st probe where possible. The request permits at most 8 steps, 100 records, a 1 MB serialized evidence package and a 20-second read/evidence budget; the existing scalar adapter also bounds each projected record to 64 KB. First-page numeric/text searches remain explicitly bounded even when the sample happens to fit. They do not claim exhaustive filtering. No continuation/pagination API is introduced in this phase; narrow the exact identifier scope for larger populations.

Current unsupported scope includes arbitrary date intervals, OEM/model/plant/priority filters, arbitrary symptom/diagnosis reasoning, negative/conditional SQL logic, population rates/aggregates/ranking, unsupported joins, physical-engine merges, coverage decisions and operational actions. A model cannot bypass these restrictions. Cross-source company/model comparison remains unverified when its exact context mappings are unavailable; serial equality is only a candidate association. Verified incorporation, comparable failure mechanisms and exposure cohorts are still missing for recurrence conclusions.

## Files and future changes

- `workflow_api/business_resolution.py`: task/fact/predicate registries, index, deterministic interpretation and dependency/field resolver.
- `workflow_api/business_intent.py`: opt-in constrained model interpretation and fallback.
- `workflow_api/business_retrieval.py`: scoped plans, metadata checks, read execution, evidence and planner context.
- `workflow_api/business_ontology_routes.py`: backend endpoints.
- `workflow_api/service.py`, `database_workflows.py`, `kg_retrieval.py`: trusted planner/metadata integration.
- `workflow_api/data_queries.py`: dotted scalar projection accounting fix.
- `scripts/ontology_retrieval.py`: shared-service terminal interface.
- `scripts/check_business_retrieval.py`: fresh isolated metadata/live acceptance.
- `tests/test_business_retrieval.py`, `tests/test_kg_retrieval.py`: independent backend acceptance/security/integration tests.
- `openspec/changes/simpson-knowledge-phase2/`: design, specification, tasks and verification.

Phase 1 classes, relationships, mappings, states, identities, schema, imports and history are reused. Editable business rules remain in `ontology/business-reference/configured-rules.json`; mappings and the knowledge authoring package remain in that directory. To change saved knowledge, explicitly import a new version; existing requests retain the old version. Resolver capability/fact/predicate registrations live in `business_resolution.py` and must have backend tests when extended.

Phase 3 can consume this evidence to construct and orchestrate workflows, including branches, parallel tasks, human decisions and controlled actions. Those capabilities, frontend integration and production activation have not been implemented or deployed by this change.

Test results and live/model evidence are recorded in [verification.md](../../openspec/changes/simpson-knowledge-phase2/verification.md).
