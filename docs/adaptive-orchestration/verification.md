# Phase 2 verification — 5 November 2026

Repository `/home/raf/agentic-ai-builder`; branch `agentic_ai_builder`; starting commit `453f37d`. The initial worktree was clean and Phase 1 was already committed. Backend only: no frontend changes, deployment, service restart, dependency installation, live model call or live external write.

The supplied Phase 2 instructions explicitly prohibited new OpenSpec documents/workflows. `AGENTS.md` requires OpenSpec artifacts; that conflict was reported before implementation and the user's explicit phase instruction was followed. Existing repository instructions, contributor documentation, OpenSpec history, Phase 1 implementation, contracts and lifecycle/recovery tests were inspected. No OpenSpec files were changed.

## Implemented behavior

The additive `evaluator-decision-v1` contract supports all six decisions and requires actual observation IDs, relevant action IDs, exact completion criteria and rationale. The existing OpenAI provider proposes JSON; backend schema, scope, dependency, receipt and completion checks remain authoritative. Unknown observations, invented authority, stale decisions, nonlocal wait schemas and premature completion are rejected.

Five durable case states are `UNDERSTAND`, `PLAN`, `GATHER_AND_ASSESS`, `EXECUTE`, `EVALUATE`. The existing LifecycleDriver supplies bounded commands; the existing GraphRunner performs execution and CrewAI remains the specialist coordination path. A case-owned permission selects one action, including its approval/condition path. Workers yield before any other action. Pinned stage output bindings, schemas and completion predicates use the same extracted validation method as ordinary stages.

`orchestration-plan-v2` links immutable compositions through stable plan ID, revision, previous fingerprint/composition, rationale and triggering observations. Superseding a reconciled run preserves completed action definitions, outputs, checkpoints, approvals that supported completed actions, and cumulative usage. Pending or already-approved unfinished actions lose their old approval authority. The successor needs normal workflow/Registry review and fresh exact-payload approval. Completed spreadsheet creation is carried forward without replay.

Evidence expansion uses registered read/reasoning capabilities. Case/stage capability and tool allowlists restrict discovery before additional source preparation. Ontology, mappings, provider, existing source connections and identifiers stay pinned. Retrieval expansion may add mapped facts while executable capability semantics remain pinned. Native retail package reads additionally enforce exact package/revision/capability inputs.

Each reasoning turn receives bounded original goal/constraints, ontology, actual observations and output digests, verified receipts, completed/skipped actions, waits, budgets and existing WorkingMemory/ExperienceMemory projections. Conservative provider reservations occur before calls and combine with runtime usage across revisions. Current server ceilings/defaults: 16 reasoning turns, four revisions, 1,000,000 reserved tokens, 32 tool calls, 64 model calls, 600 seconds, and 2,000 evaluator output tokens. Context is capped at 96,000 bytes. Narrower existing workflow/plan limits still apply.

Typed waits, scoped CAS/command receipts, persisted model intents and existing run/effect journals govern continuation. Known failures can return to evaluation; uncertain effects prohibit replanning until reconciliation. An interrupted evaluator call is retained for operator review and is never automatically repeated. Existing cancellation and workspace isolation apply.

## Exact final tests

All commands ran from the repository root using controlled providers and disposable persistence.

### Adaptive acceptance

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_adaptive_orchestration.py --basetemp /tmp/adaptive-phase2-verified
```

**24 passed, 2 warnings, 196.21 s.** Log `/tmp/adaptive-phase2-verified.log`.

Covers missing evidence → added inspection retrieval → reevaluation; successful evaluator-proposed revision; completed Sheet preservation; pending and already-approved email invalidation; typed recipient/event waits; restart without duplicate writes; stale/completed-action revision rejection; same evaluator against Simpson and native retail package fixtures; invalid decision/authority/schema rejection; reasoning/token/revision/tool budgets; idempotency; workspace isolation; cancellation; worker yield; uncertain-write revision blocking; interrupted evaluator intent; Phase 1 conditional skips; initial Phase 1 model planning; controlled OpenAI adapter validation.

A final stricter empty-action-reference guard passed **1 overlapping test, 23 deselected, 2 warnings, 1.86 s**, log `/tmp/adaptive-contract-followup.log`. It is not added to the distinct total. Earlier focused and intermediate runs are also overlapping and excluded.

### Phase 1 action plans (final confirmation)

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_connected_action_plans.py --basetemp /tmp/adaptive-final-phase1-confirmed
```

**33 passed, 10 warnings, 82.96 s.** Log `/tmp/adaptive-final-phase1-confirmed.log`.

### Existing platform

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_runtime.py tests/test_registry.py tests/test_planner.py tests/test_planner_provider_errors.py \
 tests/test_dynamic_delegation.py tests/test_delegated_tools.py \
 tests/test_business_preparation.py tests/test_business_planning.py \
 --basetemp /tmp/adaptive-final-platform
```

**184 passed, 32 subtests passed, 22 warnings, 159.32 s.** Log `/tmp/adaptive-final-platform.log`.

### Existing connectors

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_google_tools.py tests/test_inventory_report_runtime.py tests/test_supplier_discovery.py \
 connector_extension/tests/test_connectors.py connector_extension/tests/test_sheet_report.py \
 connector_extension/tests/test_sheet_creation.py connector_extension/tests/test_generalized_sheets.py \
 connector_extension/tests/test_generalized_features.py connector_extension/tests/test_application.py \
 --basetemp /tmp/adaptive-final-connectors
```

**128 passed, 6 subtests passed, 218 warnings, 442.01 s.** Log `/tmp/adaptive-final-connectors.log`.

### Existing cases, Simpson, retail, composition and recovery

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_business_cases.py tests/test_business_case_runtime.py tests/test_simpson_lifecycle.py \
 tests/test_generic_lifecycle_phase6.py tests/test_business_composition.py tests/test_agent_memory_recovery.py \
 --basetemp /tmp/adaptive-final-core
```

**148 passed, 26 warnings, 693.25 s.** Log `/tmp/adaptive-final-core.log`.

The five disjoint final suites total **517 tests and 38 subtests passed; zero final failures**. Warnings are the existing JSON Schema RefResolver and FastAPI lifespan deprecations. This is relevant regression qualification, not an all-repository or production-readiness claim.

The pre-edit targeted baseline passed **61 tests, 14 warnings, 313.74 s** (`tests/test_connected_action_plans.py tests/test_simpson_lifecycle.py tests/test_business_case_runtime.py`; `/tmp/adaptive-phase2-baseline.log`). It overlaps final suites and is not added.

## Contract and source gates

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B scripts/validate_contracts.py
git diff --check
```

Shared schema/fixture validation passed, including both new examples taken from executed revision decisions/plans. Changed Python sources parse successfully. Trace checks verify manifest hashes, linked plan fingerprints, preserved completed receipts and final persisted runtime completion.

During implementation, focused tests exposed approval-boundary lease release, skipped-branch propagation and oversized duplicated memory projections. These were corrected in the shared execution/memory boundary. Evidence expansion initially lacked pinned ontology requirements; it now retains executable contracts while validating new preparation/source pins. A 500,000-token default was insufficient for the full conservative ontology/context reservations in the expanded-evidence case; the bounded default is now 1,000,000 and explicit low-budget tests still reject before effects. Fixture setup also required the existing conditional `equals` field and explicit event-ingestion permission. No existing regression assertions were weakened. Intermediate failing runs are superseded by the final results above and are not successful qualification.

## Executed artifacts

Five complete controlled traces are in this directory:

| Artifact | Executed behavior | SHA-256 |
| --- | --- | --- |
| `simpson-trace.json` | Read → CrewAI content → approved Sheet → verified URL → CrewAI email → approved send; restart and no replay | `89c523ead47739c49b30782944f3a5107dc833eedbc7446e7eeb090cc4d43d64` |
| `gather-trace.json` | Missing evidence adds inspection read, preserves completed complaint read and resumes on revision 2 | `29852ad0dbcee3668bb82d1d608e06c1e85b484908a97ca84048b12dd84382c8` |
| `approved-revision-trace.json` | Completed Sheet preserved; an approved but unsent email is superseded, new content and approval execute once | `d039be7e1fecc1b9a9b983cf5fbf4c434df0d31022402d9892eafd1b54b9c437` |
| `retail-trace.json` | Same evaluator and runtime, native retail package/source/mapped receipt and stage output validation | `db9b409c05f05fd6c4f8d4f6f4bf579eb1801a4fb8793f71533b8abbcfd005dd` |
| `evaluator-revision-trace.json` | Evaluator changes unfinished analysis from actual complaint evidence, preserving completed read | `25f290a7ab919e2a83b064a7a62014545a3e4782714bf268e17bbdb249fd673b` |

`manifest.json` records exact raw test source paths and hashes. Repository traces include the complete test trace plus all linked immutable compositions and full run/event histories read from the same disposable SQLite databases; historical runs are not reconstructed from model statements. The repository artifact hashes therefore differ from raw test trace hashes. The retail fixture is explicitly a test package, not official company policy/data. Simpson and retail adaptive fixtures use compatible stage definitions; existing installed 12-stage and retail lifecycle definitions are unchanged and are covered separately by regression tests.

## Files changed

New implementation: `workflow_api/adaptive_orchestration.py`, `runtime/adaptive_control.py`.

Existing integration: `workflow_api/lifecycle_driver.py`, `workflow_api/business_cases.py`, `workflow_api/business_ontology_routes.py`, `workflow_api/action_plans.py`, `workflow_api/action_bindings.py`, `workflow_api/business_composition.py`, `runtime/graph.py`, `runtime/action_plans.py`, `planner/provider.py`, `connector_extension/app.py`, `scripts/validate_contracts.py`.

Contracts/examples: `shared/contracts/evaluator-decision-v1.json`, `shared/contracts/orchestration-plan-v2.json`, `shared/contracts/examples/evaluator-decision-v1.json`, `shared/contracts/examples/orchestration-plan-v2.json`.

Acceptance: `tests/test_adaptive_orchestration.py`. Documentation/evidence: this report, `README.md`, `manifest.json` and the five traces above under `docs/adaptive-orchestration/`.

No schema migration, separate case store, executor, scheduler or service was introduced. Frozen v1 contracts, installed domain processes, source mappings, credentials and frontend files are unchanged.

## Remaining work outside Phase 2

Phase 3 scheduled/recurring continuation, Gmail reply workers and separately authorized event-processing integrations remain unimplemented. Frontend integration, deployment, live model/account validation and production qualification remain outside scope. Ambiguous evaluator invocations and uncertain external effects require operator review/reconciliation; no autonomous reconciliation authority was added. Real identities, recipients, event times and provider permissions must still be supplied and authorized.
