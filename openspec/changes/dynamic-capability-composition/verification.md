# Phase 2 completion report — 4 November 2026

Implemented locally, backend only. Existing uncommitted Phase 1 work was preserved. No frontend edits, deployment, service restart, live Registry-policy/ontology import, real emails/calendar changes/external writes or paid-model evaluation. Phase 3 memory/recovery/learning was not started.

## Files changed in Phase 2

New: `workflow_api/capability_contracts.py`, `workflow_api/business_composition.py`, `workflow_api/schemas/capability-contract-v1.json`, `runtime/capability_composition.py`, `scripts/capability_composition.py`, `tests/test_business_composition.py`, `docs/simpson-business-ontology/dynamic-composition.md`, this OpenSpec change. Integration: `planner/provider.py`, `runtime/delegation.py`, `runtime/graph.py`, `runtime/service.py`, `workflow_api/service.py`, `workflow_api/business_ontology_routes.py`. Two pre-existing stale connector catalogue expectations were corrected in `connector_extension/tests/test_application.py` and `test_generalized_features.py`; production catalogue/connector behavior was not changed. Handoffs and the Phase 3 guide link were updated. Other dirty files are preserved Phase 1 changes, not new Phase 2 implementations.

## Capability contract schema

`capability-contract-v1.json`: capability ID, supported operation/purpose, kind, input/output schemas, required ontology/facts, preconditions, allowed registered tool operations, effects, verification, completion criteria, domain scope and retrieval task. Business outcome bindings are registered configuration over Phase 1 semantics. Recognized external operations require actual visible registered tool definitions and configured connectors. Unknown model IDs/descriptions never create executable capabilities. Missing inputs, unsupported operations, missing connectors, policy/schema/effect mismatches remain explicit gaps.

Task selection uses existing Phase 1 outcomes in offline diagnostics or the existing general workflow planner provider in model mode. Model proposals must contain typed registered `capability_requests`; unresolved requirements remain unsupported. The compiler adds required dependencies, checks cycles/limits and produces normal canonical workflows. Additional selected business dependencies are prepared with the existing canonical questions/resolver, not a new keyword dictionary/interpreter.

## Agent configuration factory

`AgentConfigurationFactory` registers task-specific temporary canonical definitions through the existing Registry and current policy. Each persisted configuration includes configuration/workflow/task/parent references, role/goal/capabilities, schemas, ontology pins, actual evidence references and required facts, candidate/permitted tools, completion/verification, run-only memory scope and existing reviewed limits. Proposed executable tools stay empty until normal assignment. The definition factory generates no Python code or credentials and cannot expand policy permissions.

Compositions persist as scoped, immutable hash-protected records. Repeated generation reuses identical registered versions/bindings, preserving approved grants. Approved runtime loads and workflow saving reject changed/removed composition controls, altered agents/graphs/budgets/gates, changed selected account/Sheet scope and cross-owner references. Historical noncomposition workflows retain compatibility.

## Semantic tool matching and authorization

Existing `registry.matching.compatible` and `registry.policy.authorize_tool` prove schema, capability, permission/scope/provider/quota/risk/destination/limit compatibility without issuing a grant. Connector presence and effect classification are checked; selected Google account ownership/state/scopes use existing Google binding. Tool registration and lower connector validation remain authoritative at execution.

External model-proposed recipients, calendars, IDs, ranges and content cannot become authority: they must be bound to explicit typed request operations/resources. The system asks for missing fields. Calendar creation also requires an explicit engineer reference; that reference is user context, not verified company assignment. Actual Sheets scopes/targets and operator recipient/resource ceilings remain unchanged. Creating a draft/event/row never establishes coverage approval or completed inspection.

## Delegation and CrewAI integration

Normal master-child delegation remains in `runtime/delegation.py`; no new scheduler/model loop. Composition guards filter ready children, enforce complete dependencies/one invocation per task, inject only relevant ontology and actual completed evidence, restrict tool inputs to exact prepared operations, and reject premature final synthesis. Existing pools, budgets, leases, persistence and current Registry/source authorization apply. No unrestricted recursive spawning.

CrewAI still executes through `CrewExecutor`/`CrewAdapter`; deterministic coverage stays in the mapped retrieval/backend providers. Missing mandatory decision evidence produces a deterministic needs-evidence branch without invoking that analysis model. Source reads must actually execute before claiming success; citations are checked against supplied observations; model interpretations do not become verified facts. Final task results are the actual collected outputs, not master-invented results. Model narrative remains classified as interpretation.

External write/draft operations compile to deterministic normal tool nodes after the master, each behind existing action approval. Actual provider IDs, unsuccessful/cancellation status and echoed resource identity are verified. Tool/schema errors cannot produce success. Existing effect journals/reconciliation boundaries are preserved.

## Generated examples

Actual diagnostic comparison preparation produces four specialist configurations: mapped complaint retrieval, mapped inspection retrieval, comparison and report; one coordinator delegates independent reads, then comparison, then report. IDs are composition/task-specific, not complaint-specific branches. A history goal selects history retrieval/interpretation without warranty/comparison; a warranty goal selects warranty evidence and explanation of backend coverage; a replacement goal selects replacement evidence review. Source hashes and generated-scenario provenance remain pinned.

The emitted canonical graph is `trigger → master_orchestrator → output` for read-only goals, with the internal task dependency graph in validated dynamic metadata. External actions add their normal approval/tool nodes after the master and return separate actual receipt outputs. No fixed specialist graph nodes or cosmetic fake branches are used for delegated work.

Example Registry-validated generated agent shape: `ca_<composition/task digest>`, parent `cm_<composition nonce>`, input `{task_id: constant, context: application_owned}`, typed analysis output; read specialists have the registered `business.retrieve_evidence` capability, analysis uses existing model capabilities. Candidate tools are not executable grants. Actual IDs/definitions/graph are in private `phase2-*.json` CLI artifacts.

## Backend verification

Broad backend regression:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_planner.py tests/test_registry.py tests/test_runtime.py tests/test_workflow_api.py \
 tests/test_business_planning.py tests/test_business_investigations.py tests/test_business_environments.py \
 tests/test_investigation_jobs.py tests/test_business_preparation.py
```

**214 passed, 34 subtests passed, 162 warnings, 206.43 s** (`/tmp/composition-backend-regression.log`). Covers existing investigations/Phase 1, persistence, planner contracts, authorization, budgets and runtime compatibility.

Final composition/runtime/connector regression:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_business_composition.py tests/test_dynamic_delegation.py tests/test_delegated_tools.py \
 tests/test_google_tools.py connector_extension/tests/test_connectors.py \
 connector_extension/tests/test_application.py connector_extension/tests/test_generalized_features.py
```

**125 passed, 18 warnings, 115.96 s** (`/tmp/composition-final-runtime-connectors.log`). Twenty-three composition checks at that point cover distinct arrangements, actual CrewAI bridge with fake model, parallel-ready tasks, missing/conflicting/unsupported requirements, scopes/connectors, malformed inputs/outputs/citations, exact resources, policy budgets, repeated registration, persistence, control removal, ordinary workflow planning integration and actual fake action approvals/receipts. Existing connector tests verify Calendar/Gmail/Sheets through mocked HTTP, account scopes, effect journals and normal action gates.

One additional missing-case-anchor check was added and passed with two affected repeat checks: **3 passed, 21 deselected, 2 warnings, 6.35 s** (`/tmp/composition-final-input-guards.log`). Missing anchor now produces needs_input before any company read or workflow generation. Three additional composed-scenario executions passed: complete replacement, rejected authorization as a known outcome, and conflicting physical identity selecting a backend conflict branch (**3 passed**, 24 deselected, 18.64 s; `/tmp/composition-scenario-final.log`). Distinct final total: **343 tests plus 34 subtests**; overlapping earlier/follow-up runs are not added.

Final tool-matching follow-up aligns the dry-run probe with the actual one-call/no-retry specialist allowance; comparison/history/warranty/replacement, coordination resources and approved draft checks passed again (**6 passed**, 21 deselected, 10.65 s; `/tmp/composition-matching-final.log`). These overlap the distinct total.

Configured live model calls: **zero**. One test runs actual CrewAI master/children with a deterministic `BoundedLLM`; this proves the framework integration, not live model reasoning quality. Fake Gmail draft stays paused with zero calls until the existing approval is approved, then records exactly the explicit inputs. Invalid receipt/resource tests reject unsupported success. No real provider effects occurred.

Two old extension tests expected 19 tools although the existing HEAD catalogue contains 20 (including `extension_sheets_create_report`). They now check exact catalogue IDs and correctly retain disabled creation operations when creation is not enabled. No connector, scope or approval was enabled to make those tests pass.

Shared contracts/fixtures, generated UI contract drift, strict scoped OpenSpec validation, `git diff --check` passed. No frontend build/tests were needed or claimed for this backend-only change.

## Exact terminal commands and acceptance

See [the backend guide](../../../docs/simpson-business-ontology/dynamic-composition.md#exact-terminal-checks--offline-read-only-diagnostic-registry) for prepare, inspect tasks/configurations/contracts/tools/gaps, emit workflow, validate and unsupported-operation checks. The diagnostic CLI bootstraps only an isolated read adapter Registry, never live policy. Model-backed preparation and normal save/approve/execute use the existing authenticated backend and registered server configuration.

An actual eight-operation CLI acceptance used `/tmp/simpson-evidence-coverage-20261104-01/isolated.sqlite3`: prepare, five inspection sections, emit workflow and validate. It produced ready composition `composition_5366f6490dce06969e960ec5` and workflow `cw_5366f6490dce06969e960ec5` with four specialists and one master. Private receipt: `phase2-terminal-acceptance.json`; artifacts: `phase2-{composition,tasks,configurations,contracts,selected_tools,gaps,workflow,validation}.json`. Company writes/model calls zero. This is separate from the prior phase's source checks/scenario coverage and is not counted as new live business/model acceptance.

## Remaining limitations

Only registered current domain operations and known connector semantics are executable; a new client still needs approved mappings/contracts/adapters. Model selection cannot invent missing business data or resources. Ready means executable preparation, not a guaranteed business conclusion or future remote success. Typed input confirmation/new immutable preparation resolves missing resources; there is no new in-run arbitrary input/resume engine. Multiple different inputs for the same capability are rejected as ambiguous. Agent definitions are preparation-time scoped configurations; retention/cleanup and long-term memory are separate work.

The existing policy can reject a task depth that cannot fit reviewed limits. Existing budget controls/opt-out remain; no new model token/cost ceiling. Actual registration/enabled connectors and account/resource/recipient policy are required for backend use; the diagnostic Registry is not production provisioning. UI submission of the new composition endpoints, deployment, live model/Google acceptance, Phase 3 memory/root-cause recovery and policy learning are not implemented or claimed.
