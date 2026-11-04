# Phase 6 executed verification

Executed locally on 4 November 2026, with disposable databases and controlled
external transports. No frontend change, production database migration, deployment,
live provider call or live external write was performed.

## Commands and measured results

From `/home/raf/agentic-ai-builder`:

```bash
.venv-integrations/bin/python -m pytest tests/test_generic_lifecycle_phase6.py -q --basetemp /tmp/phase6-final-verified
# 14 passed, 14 deprecation warnings, 46.77s

.venv-integrations/bin/python -m pytest tests/test_simpson_lifecycle.py tests/test_business_cases.py tests/test_business_case_runtime.py -q
# 65 passed, 14 deprecation warnings, 308.42s

.venv-integrations/bin/python -m pytest tests/test_agent_memory_recovery.py tests/test_business_composition.py tests/test_investigation_recovery_details.py tests/test_business_investigations.py -q
# 109 passed, 14 deprecation warnings, 393.05s

.venv-integrations/bin/python scripts/validate_contracts.py
# Shared contract schemas and fixtures are valid.

/home/raf/.nvm/versions/node/v22.23.3/bin/node /home/raf/.nvm/versions/node/v22.23.3/lib/node_modules/@fission-ai/openspec/bin/openspec.js validate generic-lifecycle-phase6 --strict
# Change 'generic-lifecycle-phase6' is valid

git diff --check
# exit 0
```

Existing warnings concern jsonschema RefResolver and FastAPI on_event deprecations.
Counts above are distinct across the three listed suites (188 tests). Earlier
focused runs overlap and are not added: 38 passed (case suite plus Simpson full-path),
12 passed (initial Phase 6 suite after fixing the retail output binding), and
54 passed (earlier Phase 6 plus existing memory/recovery). An initial Phase 6 run
had three retail failures because its fixture used `workflow_result.summary`;
the existing runtime actually returns `master_orchestrator.summary`. The manifest
was corrected and every new test subsequently passed. No failed run is counted.

## PostgreSQL

An initial direct `tests/test_generic_lifecycle_postgres.py -q` run reported three
explicit skips because no disposable DSN was configured. Installed PostgreSQL 16
binaries and psycopg were then verified. Private temporary clusters were created
with mode-0700 Unix socket directories and **no TCP listener**; each test created
and removed its own schema and the private cluster was stopped afterward.

The final implementation was checked with the temporary launcher
`/tmp/phase6_postgres_check.py`: **3 passed**, 6 deprecation warnings, 3.23s.
Artifacts: `/tmp/phase6-postgres-qbd7p1vh/test-result.txt` and `server.log`.
The same reproducible launcher is now repository-owned:

```bash
.venv-integrations/bin/python scripts/check_lifecycle_postgres.py
```

It runs `tests/test_generic_lifecycle_postgres.py -q -rs` with an isolated DSN,
checking reassessment/revision archives, transactional feedback, CAS concurrency,
idempotency and old-case compatibility on actual PostgreSQL. PostgreSQL experience
planning and full CrewAI execution were not exercised; SQLite acceptance covers
those paths. No production schema was opened by the disposable-cluster launcher.
The repository command was also executed: **3 passed**, 6 deprecation warnings,
2.83s; artifacts `/tmp/phase6-postgres-jy99ahpo/`. Its cluster was stopped.
Together with the three suites above, **191 distinct tests passed**. Repeated
PostgreSQL/focused runs overlap and are not added to that total.

## Actual second-domain execution and restart evidence

Case `case_7824909f7a056c5e589f35e9`, process `retail_complaint_fixture`, version 1,
ran eight stages on the same case/planner/factory/Registry/master-child/GraphRunner/
CrewAI stack used by Simpson. Actual controlled source fixtures supplied distinct
retail complaint, order, purchase and product observations. Model execution used
actual CrewAI with a controlled model transport; registered reads used the existing
package connector and trusted source adapter. No Subway records or policy are claimed.

The initial report has eight completed analytical stage results and 45 timeline
entries. Case status is COMPLETED_PROVISIONALLY; execution COMPLETED; business
outcome PROVISIONAL. Real quality evidence remained pending. Fallback artifacts
retain SYNTHETIC provenance and no commercial/physical activity is fabricated.
Eleven immutable execution feedback observations were retained by the initial drive
sequence; business-outcome rewards are all null. Operational experience contains
only run/task/checkpoint references, contracts/tool fingerprints and execution
signals, excluding synthetic facts and inferred conclusions.

Reopening BusinessCases returned the same case and feedback. Constructing a new
RuntimeService returned identical compatible experience ranks. The unchanged Phase
5 suite independently verifies a CLI subprocess reading durable state and guarded
runtime continuation. Thus local process/store restart and version pins are covered;
this is not a deployment restart or production migration test.

A late authenticated retail quality event then created reassessment
`reassessment_8034d2985679bda0e1def5ba`. Only `quality` and `monitoring` were reset.
The new monitoring composition/run required normal workflow approval and differs
from the original, which remains in its archived case revision. The complaint
stage remains byte-equivalent. Quality output is now ACTUAL event-reported evidence;
physical cause/effectiveness remain unconfirmed. The reassessment reached COMPLETED.

Additional tests explicitly cover late inspection, commercial, QA and monitoring
events; matching schema constraints; original history and unrelated work; concurrent
reassessment requests; no replay of uncertain writes; preserved completed write
state/receipts; empty source coverage; purchase-verification branching; cross-owner/
workspace experience isolation; version and capability compatibility; planner/factory
hints; revoked tool permission; synthetic reward exclusion; old composition metadata;
HTTP authentication, origin checks, scoped lookup and no-store envelopes.
Existing recovery tests cover taxonomy, provider/read failures, invalid output,
retry budgets, changed sources and checkpoint preservation. Existing Simpson tests
continue to cover repair/rejection, paid-work bounds, event deduplication, Registry
allowlists and workflow/action approvals.

## Saved evidence

Portable repository projection:
`docs/simpson-business-ontology/phase6-acceptance-trace.json`.
It contains source artifact hashes, eight original/reassessed stage results with
input/output provenance and run IDs, timeline, real waits, feedback and reassessment
comparisons. Raw repeated tool payloads are represented by ID/inputs/output digest.

Full temporary files regenerated by the acceptance test:

```
/tmp/phase6-final-verified/test_second_domain_actual_crew0/phase6-retail-report.json
/tmp/phase6-final-verified/test_second_domain_actual_crew0/phase6-retail-feedback.json
/tmp/phase6-final-verified/test_second_domain_actual_crew0/phase6-retail-reassessed-report.json
```

## Scope, storage and prerequisites

Additive service migration version 2 creates `business_case_revisions` and
`business_lifecycle_feedback`. The existing `runtime_experiences` table is reused.
No old tables, source records or saved process versions are replaced/backfilled.
Normal transaction serialization and case revision CAS remain authoritative.
Archived original cases are limited to 16 per case; feedback to 512 records per
case; experience to 2,048 records per owner/workspace; existing case size and
context limits remain. Excess new learning is bounded rather than weakening execution.

The implementation report `docs/simpson-business-ontology/generic-lifecycle-phase6.md`
lists every UI-facing backend route, response shape, component/file grouping,
client configuration, memory behavior, rewards, reassessment controls, exact tests
and deployment prerequisites. Live-provider quality, target deployment, production
load/soak, live connectors and independent physical/business outcomes remain
unverified. This is production-relevant local PostgreSQL/SQLite verification,
not a declaration of production readiness. No online reinforcement learning or UI
implementation is included.
