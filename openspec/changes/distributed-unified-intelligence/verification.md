# Distributed execution and unified intelligence — 6 November 2026 (IST)

Development implementation and controlled qualification in the existing backend.
No deployment, production service restart/migration, source-record mutation,
credential modification, paid model call or live external effect. Existing Phase
1 and concurrent Subway/frontend work were preserved. Branch at audit:
`agentic_ai_builder`, starting HEAD `1244201e87cb2968c53bbda8290c4df91574577e`.
Shared workflow/agent/tool contracts were not changed.

## Existing versus newly implemented

| Area | Reused | Phase 2 change and evidence |
| --- | --- | --- |
| PostgreSQL | Existing adapter, migrations, isolated-schema fixtures | Repaired empty-authority socket URI rewriting in auxiliary stores; reran the previously blocked 157 cases. |
| Worker scaling | Runtime/lifecycle claims, leases, fencing, singleton supervisor | Opt-in parallel runtime and dispatch consumers; pollers and other unqualified workers remain singleton. One/two/four-worker measurements and real-process claim tests. |
| Capacity | Registry limits, workflow/agent token, tool and cost budgets | Atomic queue admission and live account concurrency; bounded specialist pools; durable per-account provider minute windows; delayed retries; rotating/interleaved account polling. |
| Recovery | Phase 1 checkpoints, effect identities, unknown-intent blocking | Real Linux process kills across invocation/checkpoint/approval boundaries, interrupted delegation and event wait; fresh runtime reconstruction. No new universal reconciler. |
| Account graph | Saved ontology, preparation, package reads, semantic reviews, existing store | Owner-scoped immutable projections under one account graph ID; provenance, exact pins, freshness, conflicting observations and bounded directed traversal. No new graph database. |
| Grounding/memory | Existing planner, CrewExecutor, evidence validation, working/experience memory | Task-specific bounded graph context; pin integrity in compiled compositions; terminal run/checkpoint references linked to preparation and package graph pins. Execution outputs remain execution evidence. |
| Diagnostics | Existing health, runtime events, store metrics | Account capacity/provider windows, bounded worker progress/capacity, transaction/lock timings, graph synchronization/retrieval counts, failures and duration. |

### Defects found during verification

- `urlunsplit` changed socket URIs from `postgresql:///database` to
  `postgresql:/database`. The initial PostgreSQL attempt had **48 failures and
  109 passes**; corrected rerun passed all 157. Dedicated URI regression added.
- New provider-window DDL used the PostgreSQL keyword `window`: three new
  PostgreSQL capacity checks failed. Renamed it `minute_window`; the corrected
  seven-case run passed. These failures are retained in diagnostic logs.
- Fair polling could fill an account batch with pending approvals. It now filters
  those waits before LIMIT and interleaves accounts within the selected batch.
- Duplicate package identities produced duplicate graph node IDs and lost
  observations during traversal. One source identity now preserves its conflicting
  observations. Preparation projections also preserve earlier conflicts.
- Graph traversal could return more initial seed nodes than the requested result
  limit. Oversized seed sets now fail before traversal.
- A graph integration variable shadowed the existing working-memory task graph;
  a real CrewAI bridge test failed and caught it. The corrected bridge passed.
- The first semantic test fixture omitted the required auth `scopes` field. The
  fixture was corrected; authorization was not relaxed.

## Verification commands

All commands run from `/home/raf/agentic-ai-builder`. Pytest prefix:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider
```

Each row below appends its listed modules and `--basetemp /tmp/NAME`. Output is
redirected to `/tmp/NAME.log`. Counts are **per command**, not additive distinct
suite totals. Repeated runs, subtests and overlapping modules are not summed.

| NAME | Modules | Result |
| --- | --- | --- |
| `phase2-runtime-regression` | `tests/test_runtime.py tests/test_dynamic_delegation.py tests/test_delegated_tools.py tests/test_phase2_workers.py tests/test_distributed_execution.py tests/test_process_recovery.py tests/test_foundation_fault_tolerance.py tests/test_manual_worker_authorization.py` | 159 passed; 18 subtests; 104.33s |
| `phase2-final-focused` | `tests/test_distributed_execution.py tests/test_account_knowledge.py tests/test_process_recovery.py` | 27 passed; 44.78s; superseded for subsequently changed graph/fairness paths below |
| `phase2-final-integration` | `tests/test_business_composition.py tests/test_business_preparation.py tests/test_connected_action_plans.py tests/test_agent_memory_recovery.py tests/test_foundation_acceptance.py tests/test_simpsons_client_isolation.py tests/test_subway_client_auth.py` | 134 passed; 613.37s |
| `phase2-configuration-api` | `tests/test_live_providers.py tests/test_distributed_configuration.py tests/test_workflow_api.py tests/test_data_sources.py` | 105 case executions passed; 6 subtests; 266.73s; includes duplicate imported LiveProviderTests, subsequently removed from collection |
| `phase2-controls-qualified` | `tests/test_distributed_execution.py tests/test_phase2_workers.py tests/test_distributed_configuration.py` | 27 passed; 46.32s; final rate-column/fairness/configuration implementation |
| `phase2-intelligence-qualified-final` | `tests/test_account_knowledge.py tests/test_account_knowledge_api.py tests/test_semantic_kg.py tests/test_distributed_acceptance.py` | 24 passed; 67.98s |
| `phase2-postgres-core-qualified` | See PostgreSQL command below | 157 passed; 23 subtests; 422.61s; zero skips |
| `phase2-distributed-postgres-complete` | `tests/test_distributed_postgres.py` | 13 passed; 26.64s; zero skips |

The additional final Subway model-planning test is
`tests/test_account_knowledge.py::test_subway_supported_read_workflow_uses_actual_crewai_and_scoped_graph`,
`--basetemp /tmp/phase2-subway-planner-qualified`: **1 passed**, 7.27s. It overlaps
the graph suite and is not added to its count. It verifies the provider selection
callback receives the package graph before the actual CrewAI execution.

No skips are treated as successful qualification. Intermediate diagnostic failures
are documented separately from the corrected checks. This is not an all-repository
test claim. The pre-existing Phase 1 report remains historical evidence.

### PostgreSQL infrastructure and command

A private temporary PostgreSQL 16 cluster was initialized under `/tmp`, listening
only on its own Unix socket. Tests use a dedicated database and a role without
superuser, createdb or createrole privileges. Fixtures create unique schemas and
remove them. Production DSNs/configuration were not used. The private cluster was stopped
after verification; only this newly created test instance was shut down.

The exact core module arguments are:

```text
tests/test_phase2_postgres_concurrency.py tests/test_postgres_backend.py tests/test_durable_automation_postgres.py tests/test_generic_lifecycle_postgres.py tests/test_phase3_postgres_actions.py tests/test_phase4_postgres_journey.py tests/test_phase5_postgres_state.py tests/test_phase6_postgres_runtime.py tests/test_phase2_migration.py
```

For these commands, the existing `BUILDER_TEST_POSTGRES_DSN` was set privately in a
Python wrapper from `.local/phase2-verification/postgres.json`; then the wrapper
called `pytest.main(['-q','-p','no:cacheprovider', *modules, '--basetemp', path])`.
The DSN is not printed or copied into this report. An independently supplied
isolated disposable test DSN can reproduce the commands using the prefix above.

The initial corrected core run is `/tmp/phase2-postgres-fixed.log`: **157 passed,
23 subtests, zero skips**, 264.17s. A later combined attempt
`/tmp/phase2-postgres-final.log` had **165 passes and three new capacity failures**,
including four inherited fixture test copies. Those copies were removed from
collection. `/tmp/phase2-distributed-postgres-qualified.log` verifies the DDL fix:
**7 passed**, 13.76s. The final core and expanded distributed runs above are the
qualification evidence, without counting these overlapping attempts again.

### Process recovery and domain acceptance

Real `multiprocessing.Process.kill()` produces exit code -9. Cases cover before
execution, during the call, after the provider effect, after journal receipt,
after checkpoint and during approval wait, plus a killed delegation. Restart
preserves pinned revisions/checkpoints and consumed budgets. Unknown invocation
outcomes block instead of issuing the external action again. The controlled
provider ledger enforces the original effect identity independently.

The graph-enabled Simpson acceptance uses the actual planner/compiler and
CrewExecutor with controlled model/connector responses, reviewed report/send
approvals and a durable correlated event wait. A waiting worker process is killed;
services reconstruct; the event completes the run; duplicate delivery is rejected.
Existing Phase 1 acceptance also verifies a three-day wait without graph freshness
requirements. The graph-enabled restart uses 31 seconds; it does not bypass the
300-second freshness gate. Trace: `/tmp/phase2-intelligence-qualified-final/` under the
acceptance test's temporary directory, `phase2-graph-event-wait-trace.json`.

Subway acceptance pins the actual `subway-business-v1` revision-2 package and its
supported `subway.read.stores` capability, with explicitly controlled source rows.
The same generic runtime/Registry/CrewAI path projects saved definitions before
planning, then supplies observed record graph context to the reporting task and stores execution-memory graph references. The package contains
no executable policy rules. This does not validate real company data or invent
approval/procurement policies. Existing client-isolation suites also pass.

## Throughput evidence

Benchmark commands (JSON artifacts retained under this change's `evidence/`):

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m tests.worker_scaling_benchmark
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m tests.worker_scaling_benchmark --multi-active
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m tests.worker_scaling_benchmark --multi-active --processes
```

The baseline artifact was captured before multi-active implementation. Final
multi-active measurements enable default resource controls and fair polling.
Each point uses 16 approved jobs, actual Registry/runtime/store transactions,
150ms simulated provider I/O and a separate durable effect ledger.

| Arrangement | Workers | Jobs/sec | P95 seconds | Average queue wait seconds |
| --- | ---: | ---: | ---: | ---: |
| Existing standby, threads | 1 | 2.418 | 6.452 | 3.373 |
| Existing standby, threads | 2 | 2.687 | 5.793 | 2.801 |
| Existing standby, threads | 4 | 2.951 | 5.305 | 2.697 |
| Active, controls, threads | 1 | 1.762 | 8.766 | 4.559 |
| Active, controls, threads | 2 | 2.905 | 5.099 | 2.579 |
| Active, controls, threads | 4 | 4.072 | 3.647 | 1.844 |
| Active, controls, processes | 1 | 1.534 | 10.021 | 4.990 |
| Active, controls, processes | 2 | 2.351 | 6.405 | 3.195 |
| Active, controls, processes | 4 | 4.262 | 3.361 | 1.631 |

All points have zero duplicate effects and zero lost jobs; final controlled points
have zero retry events. Four versus one active process improves measured throughput
about **2.78×** for this workload. Final active-mode overhead is visible at one
worker. Measurements ran on one development host with other verification activity,
SQLite workflow/journal storage and simulated I/O; they are indicative, not
sustained-load, PostgreSQL-throughput or multi-host benchmarks. Latency starts at
worker launch after approval; it excludes planning/approval time. Process benchmark
DB metrics cover only the parent, not aggregate child lock waiting. Busy fraction
measures provider-effect time, not CPU utilization.

## Source and contract gates

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B scripts/validate_contracts.py
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B scripts/generate_ui_contracts.py --check
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B scripts/inventory_builder_sql.py
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B scripts/inventory_builder_sql.py --check
git diff --check
/home/raf/.nvm/versions/node/v22.23.3/bin/node /home/raf/.nvm/versions/node/v22.23.3/lib/node_modules/@fission-ai/openspec/bin/openspec.js validate distributed-unified-intelligence --strict
```

The inventory refresh includes current source SQL, including concurrent unrelated
feature additions. Inventory inclusion does not establish PostgreSQL qualification
of every SQL expression. Python AST parsing covers the current `.py` files in
`runtime`, `workflow_api`, `registry`, `planner`, `connector_extension`, `scripts`
and `tests`. Shared contracts, generated UI drift, SQL inventory (1,176 calls), whitespace and
strict scoped OpenSpec checks pass. AST parsing passed for 421 Python files.

## Changed files attributable to this phase

Source: `runtime/{capability_composition,crew,delegation,graph,memory,service,worker}.py`;
`workflow_api/{account_knowledge,resource_limits,action_plans,auxiliary_database,business_composition,client_packages,data_source_routes,lifecycle,live_providers,main,postgres,scheduler,storage,worker_control}.py`.
Only the graph integration portion of concurrent `client_packages.py` changes is
attributable to this phase. Phase 1 changes within shared files remain preserved.

New tests: `tests/test_distributed_execution.py`, `test_distributed_postgres.py`,
`test_distributed_configuration.py`, `test_process_recovery.py`,
`test_account_knowledge.py`, `test_account_knowledge_api.py`,
`test_distributed_acceptance.py`, `worker_scaling_benchmark.py`.
Docs: this OpenSpec change, its benchmark artifacts and
`docs/distributed-unified-intelligence.md`; refreshed existing SQL inventory.
No Phase 2 frontend or shared canonical-schema edits. Git working-tree diffs
retain the exact implementation for review; no commit or deployment was made.

## Acceptance and operational limits

- [x] Previously blocked PostgreSQL migration/runtime/concurrency cases execute.
- [x] Multiple active consumers preserve existing durable ownership/fencing.
- [x] Server limits, account interleaving, delayed retries and idempotent admission.
- [x] Controlled one/two/four-process throughput improvement without lost effects.
- [x] Account/owner isolation, revision integrity and bounded directed traversal.
- [x] Planner/CrewAI grounding, provenance-preserving execution memory and both domain acceptances.
- [x] Real-process kill/restart and conservative uncertain-effect handling.
- [ ] Multi-host/network/storage-failure and sustained-load qualification.
- [ ] Global credential-wide quotas and reserved tenant capacity under sustained saturation.
- [ ] Automatic external-row change capture and reviewed graph refresh across multi-day waits.
- [ ] Live-provider/model-quality/delivery acceptance and operational alert integration.
- [ ] Production migration, shared-journal deployment and rollout verification.

The global PostgreSQL advisory write lock is deliberately retained. Only qualified
runtime/dispatch consumers are parallel; planning and other background components
remain singleton. Fair bounded polling is not a strict service-level reservation.
Provider windows are per account, not shared-credential global ceilings. Graph
diagnostic counters are local to each process and need aggregation in a deployed
monitoring system.

Snapshots synchronize on authorized reads/explicit metadata refresh and expire
within 300 seconds. They do not subscribe to all external row changes. Source
metadata/current grants are checked on access; remote content changes need a new
read. Historical evidence remains available but does not authorize current work.

SMTP/Gmail/Calendar unknown outcomes still need independent provider/operator
review. Existing report read-back is the supported verified reconciliation path;
it does not automatically resume runs. Cancellation cannot retract a provider-
accepted action. No production exactly-once guarantee is claimed.

Phase 3 can build on these controlled results for production reliability and
end-to-end environment acceptance. The unchecked items above remain work; this
report does not claim complete production readiness or universal Phase 2 acceptance.
