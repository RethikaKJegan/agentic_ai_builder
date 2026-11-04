# Phase 6 generic lifecycle backend

Implemented locally on the existing Phase 1–5 components. No frontend edits,
production database changes or deployment are included. Simpson's process
`simpson_warranty_lifecycle`, version 1, remains unchanged. Execution completion,
provisional business conclusions and actual operational activity retain their
existing meanings.

Implementation files changed:

- Existing integration: `workflow_api/business_cases.py`, `evidence_completion.py`,
  `lifecycle_driver.py`, `business_composition.py`, `client_packages.py`,
  `business_ontology_routes.py`, and `runtime/memory.py`.
- New helpers: `workflow_api/lifecycle_learning.py` and `lifecycle_reassessment.py`.
- Contracts: new `client-knowledge-package-v1.json`, `lifecycle-feedback-v1.json`,
  `business-case-reassessment-v1.json`; additive optional reassessments in the
  existing `business-lifecycle-report-v1.json`.
- Fixture/configuration: `ontology/client-packages/retail-complaint-fixture-v1.json`.
- Backend tooling: `scripts/business_cases.py`, `validate_contracts.py`, and new
  `check_lifecycle_postgres.py`.
- Tests: `tests/test_generic_lifecycle_phase6.py`, `test_generic_lifecycle_postgres.py`.
- Evidence/docs: this report, `phase6-acceptance-trace.json`, the Phase 5 cross-link,
  Rethika repository handoff, and `openspec/changes/generic-lifecycle-phase6/`.

## Audit and reuse

| Concern | Existing component reused | Phase 6 addition |
|---|---|---|
| Process/case persistence | `BusinessCases`, `WorkflowStore.transaction`, SQLite/Postgres adapter | Package-installed definitions; additive revision archives and feedback tables |
| Actual evidence and fallback | `BusinessPreparation`, `BusinessRetrieval`, `EvidenceCompletion` | Reviewed actual-event input overrides with preserved comparisons; empty package reads correctly report missing evidence |
| Planning and execution | `BusinessComposition`, capability contracts, `AgentConfigurationFactory`, Registry, master/child delegation, `CrewExecutor`, `GraphRunner` | Compatible verified experience hints and deterministic tool ordering; existing validations and approvals remain mandatory |
| Short-term memory | `runtime.memory.WorkingMemory`, durable case/run/checkpoints | Bounded goal, stage evidence, direct dependencies, limitations, assignments, receipts, waits, failures, retries and budgets |
| Long-term memory | `runtime.memory.ExperienceMemory` | Versioned operational experience derived from completed run/checkpoints, without business facts or generated policy values |
| Recovery | `runtime.recovery.RecoveryService`, case resume, bounded `LifecycleDriver` | Explicit dependency reassessment; historical executions remain inspectable |
| API | Existing authenticated `/business-ontology/v1` routes | Reassessment/revision routes and additional case inspection sections |

The audit covered the requested lifecycle, evidence, composition, retrieval,
ontology, contracts, runtime/service/delegation/crew, Registry agent, CLI, Simpson
manifest and Phase 4/5 test/OpenSpec files. Phase 3 memory/recovery live in
`runtime/memory.py` and `runtime/recovery.py`. Existing deployment conventions and
`workflow_api/postgres.py` were inspected. There is no new agent loop, training
system, background paid execution service, connector, account or permission grant.

## Generic client packages

`shared/contracts/client-knowledge-package-v1.json` is the package shape authority.
Existing manifests remain valid. Optional `process_definitions` contains up to 16
full immutable lifecycle definitions; optional `memory_policy` declares enabled
state, maximum advisory recommendations (1–8) and retention (60–2,592,000 seconds).
Publication validates each process through the same case-definition validator,
including acyclic dependencies, schemas, typed bindings and effect restrictions.
Process client/domain, ontology, capability and evidence mapping references must
match the package. Workspace/owner scope is supplied by authentication and stored
in the existing package key; packages cannot select another tenant.

Stage contracts already declare tool allowlists, required capabilities, input/output
bindings, inference rules, synthetic fallback, event/wait contracts and authorization
constraints. Packages also retain their existing concepts, relationships, source
mappings, resource bindings and scalar analytical rules. These are data, not Python,
SQL, credentials or executable source adapters. An operator must separately register
current-authority source adapters and Registry tools using existing controls.

Create a case with `client_package_id` and exact `client_package_revision` to install
its declared process versions and pin the package's evidence/context. The core
lifecycle contains no retail-specific branch. The existing default ontology path
continues to support historical Simpson cases; new domains use configured packages.

The representative fixture is
`ontology/client-packages/retail-complaint-fixture-v1.json`, package revision 1,
process `retail_complaint_fixture`, version 1. It is explicitly test data, not Subway
records or official policy. Its eight stages are customer complaint, order
identification, purchase verification, product investigation, resolution assessment,
fulfillment proposal, quality feedback and recurrence monitoring. Retail concepts,
order/purchase mappings, `retail.complaint.read`/`retail.product.review` capabilities,
`client_package_read` tool and purchase/resolution branches differ from Simpson.
Quality/fulfillment/monitoring remain qualified proposals unless actual evidence
is reported. An unverified purchase skips fulfillment analysis.

## Memory and feedback

The durable case and runtime records retain full state. `WorkingMemory.case_view`
projects only the current stage and direct upstream conclusions into model context,
with explicit projection limits. Children keep their existing task/tool isolation;
signed composition metadata pins inputs and memory. Large required context fails
closed at the existing 16,000-byte conservative token bound. Agents cannot change
source evidence, pinned inputs, grants or budgets through memory.

Completed schema-checked task checkpoints and actual matching tool records can
produce `operational-experience-v1` entries in the existing experience table.
Entries contain capability/tool fingerprints, compatible pins, run/task/checkpoint
references, recovery/retry signals and expiry. They contain no source values,
inferred findings, synthetic assumptions or generated policies. Automatic validation
here certifies observed execution metadata only; the existing human validation
path for recovery candidates remains unchanged. No business outcome is certified.

Retrieval is workspace/owner scoped and requires compatible ontology, knowledge,
mapping, provider/configuration/package pins, capability contracts and tool
definitions. Expired or invalidated records are excluded. Recommendations are
advisory: the planner receives them, the factory records task-specific hints and
current tool matching still checks schemas, connector availability, permissions,
resources, side effects and quotas. The deterministic rank is
`10 * verified_successes + 2 * recovery_successes - retries`, with stable ID ties.
It ranks previously successful configurations; it does not learn a business policy.

`lifecycle-feedback-v1.json` defines persistent feedback from case/runtime records:
task completion, schema validation, tool successes/failures, receipts, coverage,
provenance counts, retries/recovery, latency, available token/cost usage, contradictions
and rejected actions. `unnecessary_tool_calls` is null because no verified minimal
tool-call oracle exists. Missing usage/cost measurements remain null/empty.
Execution reward uses observed validations/tool signals and explicit penalties;
synthetic/inferred analytical completion alone earns no positive reward.
`independently_verified_business_outcome` is always null in this implementation.
Human reports, source observations, inferred conclusions and synthetic assumptions
are separated. These records support future offline analysis; no online RL,
model-weight updates or autonomous policy optimization is installed.

Bounds: existing 64-stage/8 MB case limits; at most 16 reassessments/archives per
case, 512 immutable feedback records per case, 2,048 experience records per owner/
workspace, at most eight recommendations. Expired operational records are reclaimed
on observation. Existing recovery candidates retain their validation lifecycle;
capacity stops new observations/candidates rather than growing without bound.

## Late-evidence reassessment and recovery

First ingest an event through the existing authenticated event endpoint with exact
saved wait correlation keys. It retains submitting identity and payload provenance.
Commercial authorization events still require existing approval authority. Late
events still record `late_event_requires_downstream_reassessment`.

An explicit `reassess` command selects that saved source/event and maps payload paths
to the originating stage's declared inputs. Values must satisfy their pinned
schemas. This is an operator-reviewed comparison of reported actual evidence with
prior assumptions, not unrestricted replacement of company data.

The command atomically archives the original case revision, computes downstream
dependency closure, records previous/actual comparisons and creates a bounded
versioned reassessment. Only affected analytical/read stages reset. Original
run/composition IDs, conclusions and histories remain in the archive. Unrelated
completed stages remain byte-equivalent. New analytical compositions/runs receive
generation-specific idempotency keys and normal workflow approval gates.

Completed affected writes and their verified receipts are retained; incomplete or
uncertain affected writes stop reassessment with `CASE_UNCERTAIN_EFFECT`. They are
never replayed. Active/awaiting affected compositions stop with
`CASE_REASSESSMENT_BUSY`. Source/mapping corrections still require fresh reviewed
pins, rather than repinning an existing case. Current reports expose reassessment
status/dependencies/comparisons and the original revision reference. Reports are
rendered from current state; saved driver responses remain immutable receipts.

Existing recovery retains missing-evidence, stale-metadata, conflicting-evidence,
invalid-output, timeout/auth/schema/capability and uncertain-write failure handling.
Explicit resume uses current source/permission checks and approved retry budgets.
No available authorized progress means a clean wait/block. Driver dispatch/time/
command bounds remain unchanged; already running providers retain runtime limits.

## Backend APIs for the existing Business Investigation UI

All paths below are relative to `/business-ontology/v1`, with existing session,
origin, workspace/owner, no-store and `{request_id,status,data}` response envelopes.
The browser's existing proxy prefixes `/api/backend`. No UI code changed.

| Method | Path | Data/consumer purpose |
|---|---|---|
| POST / GET | `/client-packages` | Publish immutable manifest / list scoped package revisions |
| GET | `/client-packages/{package_id}/{revision}` | Full exact manifest and SHA-256 |
| POST | `/cases` | Existing create body, including package ID/revision and process ID/version |
| GET | `/cases/{case_id}` | Current complete durable case, revision, evidence, stages and pins |
| POST | `/cases/{case_id}/drive` | Existing bounded driver request and stop reason/report |
| POST | `/cases/{case_id}/events` | Existing correlated authenticated event command |
| POST | `/cases/{case_id}/reassess` | `business-case-reassessment-v1` body; returns current case |
| GET | `/cases/{case_id}/revisions/{revision}` | Original archived complete case snapshot |
| GET | `/cases/{case_id}/sections/history` | Archived reassessment revision IDs/statuses; not every intermediate command revision |
| GET | `/cases/{case_id}/sections/reassessments` | `items`: affected/reexecuted stages, preserved writes, comparisons and status |
| GET | `/cases/{case_id}/sections/memory` | Bounded working view and per-stage advisory recommendations |
| GET | `/cases/{case_id}/sections/learning` | Immutable `lifecycle-feedback-v1` items; limit 512; offline only |
| GET | `/cases/{case_id}/sections/recovery` | Per-stage classified errors and retry attempts |
| GET | `/cases/{case_id}/sections/report` | Current `business-lifecycle-report-v1`, optional reassessment history |
| GET | `/cases/{case_id}/sections/{section}` | Existing stages, agents, tools, evidence, assumptions, conflicts, waits, timeline and outcomes |

The workflow UI's existing workflow validate/approve, run/action approval and run
inspection interfaces remain unchanged. No case endpoint grants those approvals.
Reuse `run-memory`, `run-outcomes` and existing experience/recovery endpoints for
task-level details; case sections add lifecycle context above them.

Example reassessment body after ingesting a matching inspection event:

```json
{
  "request_key":"inspection-reassessment-001",
  "expected_revision":48,
  "source":"simpson.field_service",
  "event_id":"ACTUAL_SAVED_EVENT_ID",
  "input_bindings":{"reported_diagnosis":"findings"}
}
```

Use the actual current revision and saved payload paths/schema. Then call bounded
drive using a fresh request key; approval waits remain explicit. The CLI supports
`reassess --case-id ... --json reassessment.json` and inspect sections `history`,
`reassessments`, `memory`, `learning`, `recovery` and `report`, through either its
existing isolated or authenticated configured-backend path.

## Test commands and deployment prerequisites

```bash
cd /home/raf/agentic-ai-builder
.venv-integrations/bin/python -m pytest tests/test_generic_lifecycle_phase6.py -q
.venv-integrations/bin/python -m pytest tests/test_simpson_lifecycle.py tests/test_business_cases.py tests/test_business_case_runtime.py -q
.venv-integrations/bin/python -m pytest tests/test_agent_memory_recovery.py tests/test_business_composition.py tests/test_investigation_recovery_details.py tests/test_business_investigations.py -q
.venv-integrations/bin/python scripts/validate_contracts.py
.venv-integrations/bin/python scripts/check_lifecycle_postgres.py
```

The last command requires PostgreSQL binaries, psycopg and a non-root user. It
creates a private temporary cluster with no TCP listener, runs disposable-schema
tests and stops that cluster. Alternatively set `BUILDER_TEST_POSTGRES_DSN` to an
explicit disposable database and run `tests/test_generic_lifecycle_postgres.py`.
Without a disposable DSN those tests explicitly skip. Never point them at production.

See [verification](../../openspec/changes/generic-lifecycle-phase6/verification.md)
for exact executed results and PostgreSQL evidence, and the
[actual retail trace](phase6-acceptance-trace.json). **191 distinct tests passed**,
including three real disposable PostgreSQL checks. Live provider verification was
not performed.
Before deployment: review migrations/contracts, back up the target database,
configure trusted source adapters, Registry/credentials, real authentication,
provider budgets and authorized event/driver infrastructure; run separate reviewed
read-only integration checks against intended services. Create a fresh case with
actual accessible identifiers and read tools, inspect pins/provenance and stop at
approvals. Live write verification requires separately approved real resources.
Controlled tests do not establish production readiness or physical business success.
