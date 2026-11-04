# Phase 4 implementation and verification

Local backend implementation. No deployment, service restart, real company/source
write, actual Google/email action, paid model call or frontend edit was performed.
No Phase 5 work was begun. The full integration report, file inventory, migration,
contracts, API/CLI examples and operational limitations are in
`docs/simpson-business-ontology/persistent-lifecycle.md`.

## Broad backend checks

```bash
.venv-integrations/bin/python -m pytest \
 tests/test_business_cases.py tests/test_business_case_runtime.py \
 tests/test_business_composition.py tests/test_agent_memory_recovery.py \
 tests/test_business_preparation.py tests/test_dynamic_delegation.py \
 tests/test_delegated_tools.py -q
```

168 passed, 14 warnings, 405.47 seconds. This broad run included the then-current
38 Phase 4 acceptance cases and 130 existing compatibility checks. Later Phase 4
checks and the final focused run supersede that earlier acceptance count.

```bash
.venv-integrations/bin/python -m pytest \
 tests/test_runtime.py tests/test_registry.py tests/test_workflow_api.py \
 tests/test_business_planning.py tests/test_business_investigations.py \
 tests/test_business_environments.py tests/test_investigation_jobs.py \
 tests/test_google_tools.py tests/test_business_retrieval.py \
 tests/test_investigation_recovery_details.py -q
```

246 passed plus 34 subtests, 178 warnings, 337.44 seconds. Warnings concern existing
JSON Schema and FastAPI deprecations. These suites are scoped backend regressions,
not a claim that every repository test or a live deployment was exercised.

```bash
.venv-integrations/bin/python -m pytest \
 tests/test_business_cases.py tests/test_business_case_runtime.py \
 tests/test_business_composition.py tests/test_delegated_tools.py -q
```

89 passed, 10 warnings, 163.01 seconds. This includes 48 then-current Phase 4 checks,
email receipt-to-reply binding and existing composition/delegated-tool compatibility
after the email catalogue addition. A subsequent provenance-priority follow-up adds
three acceptance cases; the final complete Phase 4 result is recorded below.
Repeated/overlapping runs must not be added together.

```bash
.venv-integrations/bin/python -m pytest \
 tests/test_business_cases.py tests/test_business_case_runtime.py -q
```

Final result: **51 passed**, 10 existing deprecation warnings, 73.32 seconds. This
includes the three final precedence cases: deterministic derivation outranks an
upstream inferred/synthetic binding, and grounded inference outranks an upstream
synthetic binding. The corrected test manifests declare their upstream dependency;
the process validator correctly rejected the original incomplete test manifests.
All 51 Phase 4 cases pass together on the final implementation.

## Additional gates

```bash
.venv-integrations/bin/python scripts/validate_contracts.py
/home/raf/.nvm/versions/node/v22.23.3/bin/node \
 /home/raf/.nvm/versions/node/v22.23.3/lib/node_modules/@fission-ai/openspec/bin/openspec.js \
 validate persistent-business-lifecycle --strict
git diff --check
```

Contract schemas/fixtures and strict scoped OpenSpec passed. Final whitespace and
scope review passed, including newly added files. Existing shared workflow,
agent, tool and authentication contracts retain their original shapes.

## Acceptance evidence

| Requirement | Verified behavior |
|---|---|
| Case creation and restart | Real WorkflowStore state; immutable process snapshots; reconstructed services and independent CLI processes |
| Dynamic stages | Same definition/capability instantiated twice, independent compositions and run IDs |
| Durable transitions | Revision conflicts and concurrent commands dispatch only once; durable scoped receipts |
| Branches and parallelism | Actual barrier-based independent execution; false branches skip; unknown conditions wait |
| Typed bindings | Earlier outputs, intra-stage derivation, schemas and receipt/event bindings |
| Actual evidence | Existing mapped C123 fixture read through shared preparation; exact source references retained |
| Completion and policy | ACTUAL/DERIVED/INFERRED/SYNTHETIC metadata, seeded fallback, case-local policy version and no commercial authority |
| Conflicts | Actual/synthetic conflicts retained; invalid/conflicting authoritative values do not silently fall back |
| Events | Exact source/type/key matching, schema validation, duplicate receipts, durable waits, timeout continuation and late-event conflict |
| Existing agents | Real composition/factory/Registry/GraphRunner; actual CrewAI adapter with deterministic model transport for another client |
| Tools and approvals | Tool allowlist denial; real runtime action gate before a fake SMTP invocation; confirmed message ID feeds reply correlation |
| Recovery | Existing read checkpoints reused; same run resumed; uncertain external effects never replayed |
| Cancellation | Case/run cancellation shares a transaction; racing run creation rolls back without an orphan run/event |
| Isolation | Owner/workspace not-found boundaries, permission rechecks, existing HTTP authentication/origin controls |
| Existing investigation compatibility | Broad investigation, preparation, planner, runtime, Registry and memory suites pass |
| No source overwrites | Deterministic read fixtures unchanged; all generated assumptions stay in case/application storage |
| CLI | Eight independent actual CLI processes; configured-backend request mapping tested with a fake transport and existing session header |

## Practical limits

The case engine is command-driven; provider webhooks/pollers must submit events
through trusted existing infrastructure and advance ready work explicitly. There
is no new always-on paid execution daemon. Unknown external effects require
provider/journal reconciliation; no automatic remote write reconciler is claimed.
Late actual events retain a conflict and require downstream reassessment rather
than rewriting already completed conclusions.

Model quality with a live configured provider, real external writes, a live
PostgreSQL migration and official customer process acceptance remain unverified.
New clients need registered capabilities, validated knowledge/mappings and trusted
source providers. Inference is configured and grounded, and unsupported synthetic
schema constraints need an explicit fallback. Limits are 64 stage instances, four
concurrent dispatches and an 8 MB case document. Provisional values cannot supply
external-action inputs or actual business authority. Normal workflow/Registry/
action approval requirements remain; no new SME-validation gate was introduced.
