# Phase 1 — Connected Simpson knowledge backend

Implemented as an additive backend extension of the existing five-layer/twelve-module Business Ontology. No frontend, agent orchestration, natural-language resolver, source-data mutation, deployment or new graph database is included.

## What is implemented

- Explicit knowledge-package import into populated modules, preserving stable IDs and historical versions.
- A `simpson-knowledge-v1` extension inside the existing immutable ontology snapshot. Core concepts/relationships/rules retain their legacy shape; the snapshot identifies itself as `simpson-business-snapshot-v2`.
- Source-backed class hierarchy, business relationships, typed attributes, exact mappings, native identity definitions, raw status vocabularies, temporal semantics, structured readiness rules, aliases and conditional/unconditional dependencies.
- Same-key retry receipts, unchanged-package no-op receipts, expected-revision checks, atomic compare-and-swap, active-generation exclusion, current authority checks and source-stamp rechecks.
- Pinned source revisions/generations, mapping/identity reference hashes, configuration revision, policy IDs/revisions/hashes and embedded policy snapshots.
- Regeneration receives protected definitions and their source evidence. It preserves them exactly or fails without changing the current version. Existing executable rule signatures are unchanged.
- Saved-version backend inspection and bounded conversion/state/rule/association diagnostics. These do not query companies, call models or execute operational actions.
- Knowledge-aware RDF/OWL/SHACL compilation with a separate compiler key; old versions retain the existing compiler key. Existing graph/definition-query services accept both through version-aware checking.

## Existing services reused

`BusinessOntology`, owner/workspace authorization, `WorkflowStore`, immutable version/event tables, source snapshots, `BusinessCompiler`, `BusinessGeneration`, source field allowlists, conservative identity conventions, policy history, and the three fixed executable rule handlers remain authoritative. No additional application tables or shared execution-contract changes were needed.

## Authoring and runtime storage

- `ontology/business-reference/knowledge-pack.json`: curated inheritance, relationships, attributes, mappings, identity/state/time/dependency definitions and terminology.
- `ontology/business-reference/configured-rules.json`: three structured readiness definitions and configurable values, with internal provenance.
- `ontology/business-reference/source-mappings.json`: existing field catalogue, extended only with source-declared complaint narrative/status/date and inspection fields.
- `ontology/business-reference/identity-basis.json`: existing identity evidence, reused without alteration.
- `workflow_api/schemas/business-knowledge-v1.json`: inspectable schema, checked against the runtime schema in tests.

`build_business_knowledge_pack.py` reproduces the curated JSON from its source-backed construction. It is a developer authoring utility, not a runtime task. Running it overwrites the two authoring files. Alternatively edit authoring JSON directly and increment the package/configuration revision before explicit import.

Imports store complete knowledge inside `business_ontology_versions`, and receipt/audit events inside `business_ontology_events`. Runtime inspection and diagnostics never reread authoring files. Changing a file alone does not alter an existing version. Changing source/policy revisions requires a new explicit import to bind the new context. Same-key retries always retain their original version.

## Definitions added

Six new classes: PhysicalProduct, EngineInvoiceRecord, OEMAccount, ReplacementDispatchRecord, FailedEngineAnalysisRecord and InternalCutInRecord. Existing physical-engine IDs are preserved and serial descriptions no longer imply global physical identity.

The package adds 26 relationships covering complaint/OEM associations, inspection/report/observation/engineer concepts, replacement and dispatch, returned-engine QA, cause-to-corrective-action, engineering change/effectivity/applicability and monitoring population. Direct source bindings are distinct from conceptual predicates. Inverse text is descriptive; no duplicate instance edge or query grant is created.

36 mappings cover engine invoice identifiers/dates, complaint narratives/hours/dates/status, OEM account/company references, inspection narratives/dates/status, replacement modes/dispatch, QA observations/status/effectivity and cut-in scope. Only registered conversions are permitted. Null, invalid numeric values and zero remain distinct. Calendar-day dates do not fall back to another business date; timezone-free timestamps are not assigned a timezone silently.

## Identity, state and rule limits

Identity uses connection, collection, native type and native value. A direct-reference diagnostic also requires the actual reference type/value separately from the referring record's primary key. Equal identifiers in unrelated namespaces remain separate. Equal serials produce candidates, never physical-engine merges. Conflicting company/model observations remain explicit. Company/model equality is supplied evidence, not independent verification by the diagnostic.

Source enum declarations define case states, report states, dispatch states and QA approval states. No transitions are inferred from enum order. Activity completion, change applicability and incorporation retain explicitly undefined source state models where no binding is established. `PUBLISHED` means report publication, not inspection completion. A QA approval does not independently confirm a root cause.

The added rules have ordinary names: Warranty Assessment, Replacement Readiness and Inspection Report Availability. They check typed input readiness/conditions only. They have no operational effects and never produce an official-policy decision. Their `configured_logic` provenance is retained; no official policy quotation, threshold or approval is invented. Existing source-derived warranty policy revisions and three executable reference handlers are preserved. Missing applicability, exclusions, identity and incorporation facts remain missing.

## Backend interface

All HTTP operations use existing session/origin/owner authorization and no-store envelopes:

| Operation | Endpoint |
| --- | --- |
| Explicit package import | `POST /business-ontology/v1/knowledge/import` |
| Inspect complete saved knowledge | `GET /business-ontology/v1/versions/{vid}/knowledge` |
| Inspect one concept | `GET /business-ontology/v1/versions/{vid}/knowledge/concepts/{concept_id}` |
| Run pure diagnostic | `POST /business-ontology/v1/versions/{vid}/knowledge/diagnose` |

Import body: `{"expected_revision": 6, "request_key": "phase1-import-unique-key"}`. Use the actual current revision. It requires the existing write authority; it does not grant any source operation.

Diagnostic examples:

```json
{"operation":"convert","id":"mapping:complaint_hours","value":"0"}
```

```json
{"operation":"state","id":"state:inspection_report","value":"PUBLISHED","target":"COMPLETED"}
```

```json
{"operation":"rule","id":"warranty:assessment_readiness","facts":{"operating_hours":0,"assessment_date":"2026-11-03","identity_resolved":true,"policy_applicable":true}}
```

Rule facts in that example are supplied diagnostic assertions; the service does not discover or verify them. Inputs cannot override configured parameters or introduce expressions/code.

## Exact backend commands

Run from `/home/raf/agentic-ai-builder`.

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -m pytest -q -p no:cacheprovider tests/test_business_knowledge.py
```

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -m pytest -q -p no:cacheprovider tests/test_business*.py tests/test_kg_retrieval.py tests/test_database_workflows.py tests/test_database_budgets.py tests/test_data_queries.py tests/test_simpson_business_sources.py
```

Read-only inspection of the isolated integration version:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python scripts/inspect_business_knowledge.py --database /tmp/simpson-phase1-final-20261103/isolated.sqlite3 --workspace local-workspace --owner local-builder --concept inspection:inspection_report
```

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python scripts/inspect_business_knowledge.py --database /tmp/simpson-phase1-final-20261103/isolated.sqlite3 --workspace local-workspace --owner local-builder --diagnostic-json '{"operation":"convert","id":"mapping:complaint_hours","value":"0"}'
```

The CLI opens SQLite with `mode=ro` and `query_only` for inspection/diagnostics, never loads `.env`, and starts no services. Its separate `--import-package --expected-revision N --request-key KEY` action explicitly permits local application knowledge writes; it does not write company data. Do not point an old deployed backend at a newly imported knowledge version before deploying compatible backend code.

For a repeatable integration check, choose a **new** private output directory:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python scripts/check_business_knowledge.py --database .local/workflows.sqlite3 --directory /tmp/simpson-phase1-another-check --workspace local-workspace --owner local-builder --live-sources
```

This clones definitions, policies and safe metadata into the new isolated store. No company records or credentials are copied. The optional real-source probe uses existing connectors for up to the first 100 records per collection/reference, with 3-second server-operation limits, exporting aggregate type/reference counts only. Without `--live-sources`, the check uses actual saved metadata but no company connection.

## Integration evidence — 3 November 2026

The final isolated import started from actual saved revision 6 and produced revision 7, version `bov_4a7636a6f22837d1526b166d7f042f27`: 79 concepts, 45 relationships, 23 parent links and 36 mappings. Four existing application-derived policy revisions were pinned; they are not relabelled official policy.

34 mappings were observed in the saved source metadata. Two remain explicitly unavailable in that sampled metadata: `enginedetails.buildDate` and `enginedetails.engineModel`. Missing sampled fields are not proof of schema absence. Inspection failure dates include strings; the mapping supports explicit ISO parsing and reports invalid formats, without inventing a replacement field or date.

Compilation passed, backend concept inspection returned mappings, and original application ontology rows compared unchanged. The bounded real-company probe succeeded for both databases: 19 populated sampled collections and two empty collections (`failedpartanalyses`, `icacapas`). Samples are neither random nor population integrity evidence. Two of 100 sampled replacement-to-ticket references remained unresolved; no IDs were repaired or guessed. Company writes, live application writes, copied credentials and model calls were zero. The existing connections compared unchanged.

Artifacts: `/tmp/simpson-phase1-final-20261103/report.json`, `live-source-check.json`, and `isolated.sqlite3`. The new version is in this isolated test store, **not** the live application. No services were restarted or deployed.

Automated test and contract results are recorded in `openspec/changes/simpson-knowledge-phase1/verification.md` after the final run. Fixture tests use isolated synthetic databases; real metadata/source checks are reported separately above.

## Later phases

Phase 2: natural-language interpretation, synonym matching, dependency-aware selection, automatic concept-to-field resolution and query planning. Phase 3: ongoing refresh/revalidation, retrieval quality/performance evaluation and operational rollout. Neither agent orchestration nor general-purpose generated-rule execution is included here.

## Files changed

New backend files: `workflow_api/business_knowledge.py`, `workflow_api/business_knowledge_model.py`, and `workflow_api/schemas/business-knowledge-v1.json`.

Existing backend files extended: `business_compiler.py` (validation/export/compiler keys), `business_rules.py` (version-aware compiler compatibility), `business_generation.py` and `business_extraction.py` (protected regeneration), and `business_ontology_routes.py` (four backend operations).

New authoring/utility/test files: `ontology/business-reference/knowledge-pack.json`, `configured-rules.json`, `scripts/build_business_knowledge_pack.py`, `scripts/check_business_knowledge.py`, `scripts/inspect_business_knowledge.py`, and `tests/test_business_knowledge.py`. Existing `source-mappings.json` was extended. Documentation and OpenSpec artifacts accompany these changes. Frontend, shared execution contracts, connector credentials and the original three-layer ontology were not modified.
