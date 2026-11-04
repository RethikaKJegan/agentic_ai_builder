# Phase 1 implementation verification — 4 November 2026

Local backend implementation only. No frontend changes, deployment, service restart, live Registry/ontology import, company writes or paid-model calls. No Phase 2 agent factory, memory, recovery engine or client-onboarding implementation was started.

## Files changed

New: `workflow_api/business_preparation.py`, `workflow_api/schemas/business-preparation-v1.json`, `tests/test_business_preparation.py`, `docs/simpson-business-ontology/shared-preparation.md`, and this OpenSpec change. Integrated through `workflow_api/investigation_coverage.py`, `business_investigations.py`, `business_ontology_routes.py`, `business_planning.py`, `service.py`; `planner/service.py`, `planner/provider.py`; `runtime/service.py`; and `scripts/simpson_investigation.py`. Updated a stale default-tool assertion in `tests/test_workflow_api.py`, plus repository documentation/handoffs.

## Reused components and audit

Existing knowledge-package builder, five-layer ontology/version store, intent interpretation, fixed-point dependency traversal, stable fact IDs, source mappings/native reference checks, source query validator, evidence requirement registry/coverage providers, immutable scenario releases and current source authority. Existing general planner, workflow graph contracts, Registry discovery/assignment, CrewAI adapter and master-child delegation are reused. No parallel ontology resolver, planner or orchestration engine was introduced. Before this change the general path received metadata context but not the investigation preflight's evidence coverage.

## Shared interfaces and result schema

`SharedBusinessPreparation.prepare/get/checked/context/general_context` supplies both planning paths. `InvestigationCoverage.preflight` delegates to that instance. Result contract: `schemas/business-preparation-v1.json`, with interpreted goal/outcomes, authenticated workspace/owner scope, descriptive client/domain labels, per-task concepts/relationships/providers/facts/dependencies/mappings/supported read paths/rules, actual available evidence, structured gaps/coverage, capabilities, visible permitted Registry candidates, provenance and version/source/observation pins. Tenant follows the existing workspace boundary, not a newly invented tenancy service.

Deterministic closure remains in the existing resolver with cycle/item bounds. Definitions are deduplicated by stable ID in planner projections while retaining every required reference. Full scoped preparation persists under the existing hash-protected preflight receipt. Missing identifiers produce needs_input without company reads. Current source access/metadata failures are structured errors, not fabricated evidence. Known negative decisions retain known outcomes. Gaps retain coverage fact/state/impact and separate mapping-resolution requirements.

`BusinessEvidenceAdapter.invoke` accepts only preparation ID and a prepared task; it rechecks scope, pinned knowledge/provider, current metadata and scenario hash, then calls existing fresh source/scenario retrieval. `BusinessEvidenceConnector` implements existing graph/delegation bind/reservation/invoke protocol and rejects other preparation IDs. The exported schema-valid tool definition must be registered/enabled under operator-owned Registry policy before model tool selection; no executable grants or live policy changes are created here.

## Integration and persistence

- Investigation API/jobs/CLI preparation and general WorkflowService planning share the same instance. A test spies on that exact instance while generating both kinds of workflows.
- Both planners receive shared dependencies, evidence, coverage, registered capabilities/candidates and pins. Investigation planning retains existing graph/catalogue validation. General hierarchy planning still uses the existing dynamic delegation infrastructure.
- Provider-authored pins are discarded; server-owned preparation references are attached after proposal generation. Recorded general-workflow pins cannot be changed/removed on save. Approved runtime revisions check pin integrity; actual adapter execution additionally checks current source authority.
- General planning contribution traces use the selected ontology and pinned policy snapshots. Retries retain original prepared context through existing planner idempotency.
- Unrelated goals/unconfigured business knowledge preserve general planning compatibility with explicit unsupported/not-configured preparation state. Explicit bad scope/version/scenario selections fail. Legacy investigation plans without shared preparation remain compatible.

## Backend verification

Final relevant platform run:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_planner.py tests/test_registry.py tests/test_runtime.py tests/test_workflow_api.py \
 tests/test_business_planning.py tests/test_dynamic_delegation.py tests/test_delegated_tools.py \
 tests/test_business_retrieval.py
```

**236 passed, 34 subtests passed, 162 warnings, 147.55 s.** Log: `/tmp/shared-preparation-final-platform.log`.

Final business integration run:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_business_investigations.py tests/test_business_environments.py \
 tests/test_investigation_jobs.py tests/test_business_preparation.py
```

**72 passed, 10 warnings, 186.53 s.** Log: `/tmp/shared-preparation-final-business.log`. Two additional authority tests subsequently added and passed: candidate discovery requires current Registry roles/scopes, and an approved runtime rejects a changed preparation pin. **2 passed, 17 deselected, 2 warnings, 3.30 s** (`/tmp/shared-preparation-authority-final.log`). Total verified distinct tests across those final runs: **310 plus 34 subtests**. Warnings are existing FastAPI lifespan/jsonschema deprecations; no all-repository green claim.

After final adapter output-schema and runtime pin-removal checks, the complete new preparation module passed **19 tests** (26.19 s), and the final affected runtime/preparation run passed **74 tests plus 18 subtests**, 22 warnings, 45.32 s (`/tmp/shared-preparation-runtime-final.log`). These follow-up runs overlap the counts above and are not added to the distinct total. Both changed and removed pins are rejected at approved runtime load.

Coverage includes comparison, warranty, replacement and paraphrases; no identifiers; complete/missing/conflicting/rejected scenario evidence; forbidden extra query arguments; foreign owner/scope; source revocation/stale metadata; new ontology heads with original version retention; captured observations versus fresh source values; shared general/investigation preparation; hierarchy draft validation; idempotent retries; schema/export validation; source/scenario provenance; existing investigation compatibility and existing delegation/tool boundaries. Model transports are deterministic. Actual CrewAI bridge tests use offline transports; no new live model-quality result is claimed.

Integration defects found and fixed before final verification: repeated ontology definitions exceeded the existing model-planning context bound, so the shared planner projection now deduplicates full definitions and preserves their ID dependencies. The old API test expected no tools despite the pre-existing default registration of four database tools; it now asserts exactly those built-ins and no custom provider. No default tool policy was changed to satisfy that assertion.

Shared contract schemas/fixtures, generated UI contract drift, strict scoped OpenSpec validation and `git diff --check` passed. Frontend files unchanged; no frontend build/test claim for this backend-only task.

## Exact terminal commands and acceptance

See [the backend guide](../../../docs/simpson-business-ontology/shared-preparation.md#backend-commands) for existing CLI preparation, concepts/facts/mappings/evidence/gaps/capabilities/tools/pins inspection, fresh adapter retrieval, offline plan/graph/validation and the normal authenticated general planning request envelope.

An actual 12-operation CLI smoke test used the prior private isolated scenario release in `/tmp/simpson-evidence-coverage-20261104-01`: preflight, eight inspection sections, adapter retrieval, offline workflow planning and validation. All passed; schema business-preparation-v1; preparation `preflight_d592d6af4af8a0d1f4cc68b9`; workflow `investigation_45d821375e4974ce5e7e95df`. Company writes/model calls zero. Private outputs are `shared-phase1-*.json` there. No company-source evidence was sent to a model. Existing independent source verification and 24-case/72-task coverage from the prior phase are not counted as new live integration/model tests here.

## Remaining limitations

Only currently supported business task contracts are available; client/domain labels do not create new domain semantics. Existing Simpson vocabulary/task dictionaries are not replaced by a generic agent factory in Phase 1. Nonbusiness fallback is compatibility, not a claim of grounded business execution. Tool discovery is not assignment. The new retrieval tool requires normal operator Registry enablement/scopes; operational writes remain outside this adapter. Automatic cross-owner/automation access to another owner's preparation is not added. Real missing evidence is not synthesized; scenarios remain isolated and distinguishable. Existing per-read/call/time and context-byte bounds remain, without adding a model token/cost ceiling. UI integration/deployment, Phase 2 agent composition, long-term memory and policy learning remain separate work.
