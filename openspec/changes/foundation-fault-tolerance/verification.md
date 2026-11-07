# Foundation verification and fault tolerance — 6 November 2026 (IST)

Local backend implementation only. No deployment, service restart, production
migration, credential modification, paid model call or live provider effect.
Existing npm-cache changes and the two untracked company dump archives were
present before work and were left alone. No shared contract was changed.
Additional Subway ZIPs and an unrelated `subway-code-ontology` OpenSpec directory
appeared during verification and were also left untouched.

**Result: 689 distinct tests passed, including 35 new cases; 157 distinct
PostgreSQL cases skipped for missing test infrastructure.** No final executed
test failed. The union contains 846 collected node IDs, deduplicated across the
completed suites in `/tmp/foundation-phase1-distinct-collected.log`; repeated
focused runs and repeated skips are not added. This is scoped foundation
verification, not an all-repository test claim. PostgreSQL qualification remains
an explicit incomplete acceptance requirement.

## Confirmed defects and changes

1. Graph execution persisted an invocation intent, then dispatched without a
   second ownership/Registry check. Cancellation, lease expiry or revocation at
   that boundary could still reach the adapter. Dispatch now revalidates running
   state, live owner lease, current grants and the immutable revision digest.
2. Graph/delegation checked worker identity without requiring an unexpired lease.
   The same owner could checkpoint a late result after expiration. All execution
   ownership checks and lease renewal now require a live lease.
3. Delegated failure paths loaded a run and wrote failure state without ownership
   fencing. They could mutate cancelled/taken-over execution. Both child-agent
   and child-tool failure commits now check the current live owner.
4. Delegated confirmed-usage settlement was also unfenced. A delayed model
   response could refund reserved tokens after cancellation/takeover/expiry.
   Settlement now uses the same current-ownership, revision and deadline gate.
5. A live lease did not prevent an overlong adapter response from completing
   beyond an agent/workflow deadline. Dispatch and result acceptance now enforce
   unchanged execution deadlines. Post-invocation denial records the underlying
   safe error code and blocks without claiming a successful checkpoint.
6. Unknown timeout modes, timeout controls on nonapproval nodes, and missing
   timeout/error paths passed document validation. They now fail before execution
   with `UNSUPPORTED_EXECUTION_CONFIGURATION`. Existing supported stop/retry/
   rejection-branch timeout behavior is retained and covered by regressions.
7. Operator reconciliation lacked a scoped summary and the existing setup CLI
   could not select runtime report effects. Added read-only
   `GET /runs/{run_id}/recovery` and extended the existing command with report,
   workspace and exact effect identity support. Provider marker/content reads
   verify a report before its local journal receipt changes; no provider mutation
   or automatic workflow resume is added.
8. SQL inventory represented 380 calls while current source contains 1,117.
   AST comparison found 751 added/changed and 14 removed/changed calls, including
   accumulated ontology, source, case, automation, memory and isolation modules.
   The generated inventory was refreshed, retaining the drift check. This does
   not establish that every inventoried SQL expression is PostgreSQL-qualified.

The first seven fencing/dispatch regressions failed before their implementation
fix, all four failure-policy cases failed before validation fixes, both deadline
cases failed before deadline checks, and all three settlement cases failed
before settlement fencing. The five CLI cases exposed unsupported command
arguments before report support was implemented. Initial crash-test failures
also exposed a test clock exceeding the unchanged workflow deadline: the test
now uses a 30-second lease and a 31-second advance, without increasing budgets.
Intermediate failures are not counted as successful qualification.

## Implementation status

| Component | Previously implemented | Changes made | Verification |
|---|---|---|---|
| State machine | Durable legal transitions and audit | Live ownership/deadline guards | Runtime and worker suites |
| Checkpointing | Node/task checkpoints, pinned revisions | Reject expired/late completions | Crash matrix; memory and recovery suites |
| Failure recovery | Targeted safe recovery and unknown-write blocking | Scoped operator evidence and report read-back command | Fault, recovery and command tests |
| Idempotency | Run/event uniqueness and connector journals | Retained existing identities; added boundary tests | Duplicate request/event, journal/restart tests |
| Concurrency control | Transactions, CAS, claims and leases | Fence failure and usage settlement; require unexpired leases | Runtime, workers, lifecycle and controlled races |
| Workflow execution | DAG branches/joins; bounded specialist concurrency | Validate supported failure paths before execution | Planner/API, runtime and supported timeout tests |
| Agent delegation | Existing CrewAI and specialist coordination | Fence success, failure and usage settlement | Actual CrewAI with controlled model responses |
| Tool contracts | Backend input/output/permission/resource checks | Exact report identity in operator reconciliation | Connector and reconciliation suites |
| Human intervention | Durable approvals, typed waits and events | Combined planner → approval → wait → restart acceptance | Durable/adaptive suites and new acceptance |
| Tenant isolation | Workspace/owner guards and dedicated client identities | Scope recovery diagnostics; test cross-workspace denial | Simpson/Subway and recovery endpoint tests |
| PostgreSQL reliability | Existing adapter/migrations/concurrency fixtures | Updated inventory, attempted current tests | BLOCKED: 157 distinct cases skipped, including seven migration cases; no test DSN |

## Files changed

Source:

- `runtime/service.py`: shared live-ownership and deadline checks.
- `runtime/graph.py`: dispatch revalidation, lease fencing, deadline acceptance
  and structured post-invocation denial evidence.
- `runtime/delegation.py`: fence delegated completion, failure and confirmed
  usage settlement; preserve conservative reservations after ownership loss.
- `runtime/recovery.py`: read-only scoped recovery/reconciliation diagnostics.
- `runtime/history.py`: reject unsupported recovery query parameters.
- `workflow_api/main.py`: authenticated additive recovery GET route.
- `workflow_api/service.py`: reject unsupported timeout/error configuration.
- `connector_extension/reconcile_sheet_setup.py`: extend existing operator
  read-back command for report exports with exact workspace/effect references.

Tests and evidence:

- `tests/test_foundation_fault_tolerance.py`: deterministic crash matrix,
  cancellation/revocation dispatch races, expired/taken-over workers, delegated
  failure/settlement, deadline overruns, failure-policy validation, diagnostic
  endpoint authorization and tenant isolation.
- `tests/test_foundation_acceptance.py`: controlled planner/CrewAI/approval/event
  scenario with service reconstruction, preserved effects/checkpoints and budgets.
- `tests/test_effect_reconciliation_command.py`: actual report adapter/journal
  read-back through the command, including wrong scope/effect/content rejection.
- `tests/test_durable_automation.py`: optional controlled planner hook in the
  existing acceptance helper; existing callers retain their behavior.
- `openspec/changes/phase2-backend-reliability/sql-inventory.json`: regenerated
  inventory; no database migration or SQL execution.
- This change's `proposal.md`, `tasks.md`, specification and verification report.
- `docs/foundation-fault-tolerance.md`: operational recovery procedure and limits.

## Commands and results

Commands run from `/home/raf/agentic-ai-builder` using the existing environment.
Every pytest command uses this prefix (no pytest cache or Python bytecode):

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider
```

Append the following exact arguments to that prefix. Shell output was redirected
to the named `/tmp/foundation-phase1-*.log` file using `> PATH 2>&1`.

### Baseline

```text
tests/test_runtime.py tests/test_registry.py tests/test_dynamic_delegation.py tests/test_delegated_tools.py tests/test_agent_memory_recovery.py tests/test_business_cases.py tests/test_business_case_runtime.py tests/test_adaptive_orchestration.py tests/test_durable_automation.py tests/test_phase2_reliability.py tests/test_phase2_workers.py tests/test_simpsons_client_isolation.py tests/test_subway_client_auth.py --basetemp /tmp/foundation-phase1-baseline
```

`/tmp/foundation-phase1-baseline.log`: **299 passed, 28 subtests passed**, 94
warnings, 674.08 seconds. No failed or skipped tests. This run began before
implementation edits; subsequent affected suites below qualify the fixes.

### Final runtime and fault injection

```text
tests/test_foundation_fault_tolerance.py tests/test_dynamic_delegation.py tests/test_delegated_tools.py tests/test_runtime.py tests/test_phase2_workers.py --basetemp /tmp/foundation-phase1-runtime-qualified
```

`/tmp/foundation-phase1-runtime-qualified.log`: **143 passed, 18 subtests passed**,
30 warnings, 80.13 seconds. Includes all **29 new fault/validation cases**; zero
failures or skips. Earlier overlapping 121- and 183-test runs are not added.

### Broad integration

```text
tests/test_registry.py tests/test_agent_memory_recovery.py tests/test_business_cases.py tests/test_business_case_runtime.py tests/test_adaptive_orchestration.py tests/test_durable_automation.py tests/test_connected_action_plans.py tests/test_business_composition.py tests/test_business_preparation.py tests/test_simpson_lifecycle.py tests/test_generic_lifecycle_phase6.py tests/test_lifecycle.py tests/test_phase2_reliability.py tests/test_phase2_migration.py tests/test_phase3_actions.py tests/test_phase4_journey.py tests/test_phase5_state.py tests/test_phase6_runtime.py tests/test_simpsons_client_isolation.py tests/test_subway_client_auth.py tests/test_planner.py tests/test_planner_provider_errors.py tests/test_workflow_api.py --basetemp /tmp/foundation-phase1-integration
```

`/tmp/foundation-phase1-integration.log`: **391 passed, 7 skipped, 25 subtests
passed**, 350 warnings, 1,268.14 seconds. The seven skips are the PostgreSQL
migration cases below, not successful migration checks. This run began after
initial fencing fixes. The final deadline/settlement changes were made while it
was running; affected execution/memory/durable suites are rerun separately below.

### Final durable and end-to-end acceptance

```text
tests/test_foundation_acceptance.py tests/test_connected_action_plans.py tests/test_adaptive_orchestration.py tests/test_durable_automation.py --basetemp /tmp/foundation-phase1-durable-qualified
```

`/tmp/foundation-phase1-durable-qualified.log`: **85 passed**, 14 warnings,
544.89 seconds; zero failures or skips. This run uses the final deadline and
settlement implementation.

The combined acceptance uses the existing planner/compiler, current registered
capabilities, actual CrewExecutor and controlled model responses. It reaches
exact-payload approvals, executes one report and one send, persists a typed event
wait, reconstructs runtime/case/automation/worker services, advances three days,
accepts a correlated provider event, completes the same workflow and rejects a
duplicate event. Completed action instances and workflow digest remain identical;
consumed counters do not reset. The test writes the complete actual trace to
`/tmp/foundation-phase1-durable-qualified/test_planned_objective_survive0/foundation-acceptance-trace.json`.

The independent initial acceptance passed **1 test**, 6 warnings, 22.24 seconds.
It overlaps the final durable suite and is not added to its count.

### Final memory, generic execution and client isolation

```text
tests/test_agent_memory_recovery.py tests/test_business_composition.py tests/test_generic_lifecycle_phase6.py tests/test_simpsons_client_isolation.py tests/test_subway_client_auth.py --basetemp /tmp/foundation-phase1-memory-qualified
```

`/tmp/foundation-phase1-memory-qualified.log`: **95 passed**, 70 warnings,
379.73 seconds; zero failures or skips.

### Connector safety and reconciliation

```text
tests/test_google_tools.py tests/test_google_connections.py tests/test_inventory_report_runtime.py tests/test_supplier_discovery.py connector_extension/tests/test_connectors.py connector_extension/tests/test_sheet_creation.py connector_extension/tests/test_sheet_report.py connector_extension/tests/test_tracking_recovery.py connector_extension/tests/test_generalized_sheets.py connector_extension/tests/test_generalized_features.py connector_extension/tests/test_application.py --basetemp /tmp/foundation-phase1-connectors
```

`/tmp/foundation-phase1-connectors.log`: **149 passed, 6 subtests passed**, 222
warnings, 377.91 seconds. This precedes the CLI extension; its affected adapter/
command checks were rerun after that extension:

```text
tests/test_effect_reconciliation_command.py connector_extension/tests/test_sheet_report.py connector_extension/tests/test_sheet_creation.py --basetemp /tmp/foundation-phase1-command-final
```

`/tmp/foundation-phase1-command-final.log`: **38 passed, 6 subtests passed**, 2
warnings, 9.73 seconds. This includes five new command cases and overlaps the
connector suite; do not add the totals as distinct tests.

### PostgreSQL attempt and blocker

```text
tests/test_phase2_postgres_concurrency.py tests/test_postgres_backend.py tests/test_durable_automation_postgres.py tests/test_generic_lifecycle_postgres.py tests/test_phase3_postgres_actions.py tests/test_phase4_postgres_journey.py tests/test_phase5_postgres_state.py tests/test_phase6_postgres_runtime.py --basetemp /tmp/foundation-phase1-postgres
```

`/tmp/foundation-phase1-postgres.log`: **150 skipped**, 6 warnings, 2.40 seconds.
No PostgreSQL execution success is claimed. Neither the private test DSN nor
the test-only fallback connection file is configured. Production configuration
was not used. Exact collected node IDs are in
`/tmp/foundation-phase1-postgres-collected.log`.

| Blocked module | Cases |
|---|---:|
| `test_phase2_postgres_concurrency.py` | 14 |
| `test_postgres_backend.py` | 109 |
| `test_durable_automation_postgres.py` | 4 |
| `test_generic_lifecycle_postgres.py` | 3 |
| `test_phase3_postgres_actions.py` | 7 |
| `test_phase4_postgres_journey.py` | 6 |
| `test_phase5_postgres_state.py` | 3 |
| `test_phase6_postgres_runtime.py` | 4 |

The broad integration command also collected **seven** PostgreSQL migration
cases in `tests/test_phase2_migration.py`. They were skipped for the same absent
DSN, making **157 distinct infrastructure-blocked cases**, not 150 successful
database tests. Their explicit diagnostic rerun used:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -rs -p no:cacheprovider tests/test_phase2_migration.py --basetemp /tmp/foundation-phase1-migration
```

`/tmp/foundation-phase1-migration.log` records the exact skip locations/reasons;
this repeat is not added to the distinct skipped count.

Supply `BUILDER_TEST_POSTGRES_DSN` privately for an isolated disposable database
and a restricted role with schema creation/drop rights. Existing fixtures create
unique schemas and remove them afterward, including auxiliary-store schemas.
Never supply production credentials or treat historical 129 passes as current
qualification. Other unrelated PostgreSQL feature suites were not part of this
150-case foundation attempt.

### Contract and source gates

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B scripts/validate_contracts.py
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B scripts/generate_ui_contracts.py --check
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B scripts/inventory_builder_sql.py
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B scripts/inventory_builder_sql.py --check
git diff --check
/home/raf/.nvm/versions/node/v22.23.3/bin/node /home/raf/.nvm/versions/node/v22.23.3/lib/node_modules/@fission-ai/openspec/bin/openspec.js validate foundation-fault-tolerance --strict
```

Shared contracts, generated UI schema drift, inventory and strict scoped OpenSpec
validation passed. Python AST parsing checked **399 files** across `runtime`,
`workflow_api`, `registry`, `planner`, `connector_extension`, `scripts` and `tests`
with no errors. Final whitespace checks pass. No frontend source or generated UI
schema was changed.

## Required failure variants and coverage

| Variant | Actual coverage |
|---|---|
| Missing evidence | Adaptive added-read/reassessment, package missing evidence and blocked composition tests |
| Revoked permissions | Post-intent revocation regression; recovery and connected-plan denial tests |
| Invalid agent output | Existing real-CrewAI feedback/correction and bounded failure tests |
| Duplicate events | New combined acceptance plus durable automation event deduplication |
| Expired/taken-over leases | New graph, child, tool and settlement regressions; existing worker claim races |
| Uncertain external writes | New journal/crash matrix; existing uncertain Gmail and reconciliation refusal tests |
| Exhausted budgets | Existing recovery retry allowance, evaluator token/revision limits and case-wide tool budget tests |
| Human waits and cancellation | Three-day reconstruction acceptance, approval timeout/rejection and cancellation races |

The crash matrix covers before intent, after intent/before invocation, during
call, after provider acceptance/before response, after response/before journal
receipt, after journal receipt/before checkpoint, and after checkpoint/before
downstream completion. Additional tests cover interrupted delegation, cancellation,
lease expiry/takeover and persisted human/event waits. A `BaseException` simulates
termination; these tests do not claim real OS kill/power-loss or multi-host tests.

## Remaining limitations and acceptance checklist

PostgreSQL qualification is blocked by missing test infrastructure. Live-provider
quality/delivery and host/storage failures require environment acceptance. Unknown
SMTP/Gmail/Calendar outcomes have no new universal remote reconciler: they remain
blocked for independent provider/operator review. Verified report read-back only
repairs its existing connector journal, without automatically resuming the run.
External cancellation cannot retract a provider-accepted action or close the
nontransactional interval after final checks. No production exactly-once or
load-test claim is made. Multi-active workers, distributed fairness/backpressure
and expanded unified intelligence remain Phase 2 work.

- [x] Supported deterministic crash boundaries recover or block explicitly.
- [x] Completed work, checkpoint identities and pinned versions are preserved.
- [x] Uncertain effects are not automatically repeated; reconciliation is explicit.
- [x] Expired owners cannot commit results, failures or usage settlement.
- [x] Existing retries and budgets remain bounded; no budgets were increased.
- [x] Agent/tool contracts and unsupported execution configuration are checked.
- [x] Final durable human-wait and memory/client reruns completed.
- [x] Broad integration results recorded, including seven migration skips.
- [ ] PostgreSQL tests executed successfully (blocked: 157 distinct skips).
- [x] No workflows, company data, credentials or production services changed.

Counts from overlapping suites are deduplicated, rather than summed. A skipped database
test is not a successful reliability qualification. This report does not claim
an all-repository, live-provider or production-readiness result.
