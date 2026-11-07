# Distributed execution and account knowledge

This extension reuses the current runtime, Registry, lifecycle claims, ontology,
source readers, connector journals and memory. It is opt-in. No deployment or
production configuration change is included.

Set trusted server environment `BUILDER_WORKER_MODE=multi-active` to allow every
worker process to consume runtime runs and lifecycle dispatch jobs. Other
components retain the existing active/standby coordinator lease. Keep each
process connected to the same PostgreSQL database and the same durable connector
journal stores. Host-local SQLite paths do not become shared across machines.
`BUILDER_WORKER_CONCURRENCY` bounds each consumer pool (1–32, default 1).

Server-owned limits:

| Setting | Default | Meaning |
| --- | ---: | --- |
| `BUILDER_ACCOUNT_QUEUE_LIMIT` | 256 | Queued runtime runs per account |
| `BUILDER_ACCOUNT_CONCURRENCY` | 8 | Live leased runtime runs per account |
| `BUILDER_AGENT_CONCURRENCY` | 4 | Concurrent specialists within a delegation |
| `BUILDER_PROVIDER_RATE_LIMITS` | `{}` | JSON provider ID → calls/minute/account |
| `BUILDER_UNIFIED_KNOWLEDGE` | 1 in multi-active, otherwise 0 | Enable account projections |

Limits do not accept model/workflow overrides. Queue admission returns 429; retry
with the original idempotency key. Capacity deferrals use durable `available_at`
and bounded delay, without increasing execution budgets. The original workflow
and agent deadlines still apply. Mid-delegation failures remain bounded and may
require review; there is no universal automatic continuation of partial agent
sessions. Provider windows are fixed-minute per account, not global credential
quotas. Configure rates for the actual trusted Registry/model provider IDs.

Runtime polling rotates accounts. Waiting approvals and future retries cannot
fill the fair runnable batch. The PostgreSQL global advisory write lock remains:
additional processes overlap external I/O, but database writes are still
serialized. Further lock narrowing needs independent invariant qualification.

## Account graph

One account graph ID contains owner-scoped immutable projections of reviewed
preparation evidence, client-package reads and saved semantic metadata. Owners do
not inherit each other's source grants. Same-source identities may aggregate
observations; different source identities are not merged merely by matching IDs.
Conflicts remain explicit. Technical references and inferred business meanings
are separate edges. Reviewed semantic direction and provenance are preserved.

`GET /account-knowledge` lists the current owner's manifest and execution memory
references. `POST /account-knowledge/refresh` takes an empty body and synchronizes
current authorized semantic metadata. It performs no model inference or source
mutation. `POST /account-knowledge/traverse` takes exactly `pin`, `seeds`, `depth`
and `limit`. Maximum depth is 4, result bound 64, seed bound 16, default internal
time budget 100ms. Public traversal includes confirmed edges only.

Saved client-package definitions are projected before planning without claiming
that records have been observed. Preparation and package record projections
synchronize on their authorized evidence reads. Changed content creates a new revision and invalidates old current pins;
metadata is revalidated on use. Package source ownership/availability and read
permissions are rechecked. Snapshot freshness is at most 300 seconds. There is
no change-data-capture subscription for arbitrary external row changes; a fresh
read is needed to observe those changes. Historical access preserves evidence,
not current execution authority. A long human wait does not bypass stale pins:
refresh/review evidence before continuing if current graph evidence is required.

Planning receives graph context before selecting capabilities. CrewAI receives
bounded task-specific context using current session authority. Graph context is
reference data; Registry grants, approvals, schema validation, deadlines and
execution budgets still govern actions. Completed workflow references and
checkpoint hashes are labeled execution evidence, not verified business facts.

## Recovery and operations

Inspect `/worker-health`, account capacity diagnostics and durable
`run.backpressure` events. Store metrics expose transaction and lock wait time; graph diagnostics expose
synchronization/retrieval counts, failures and elapsed time.
Use existing scoped run recovery diagnostics and the Phase 1 reconciliation
procedure in `foundation-fault-tolerance.md`. Never repeat unknown sends or
calendar mutations on the assumption that process death means provider failure.
Report read-back repairs only a verified connector receipt and does not resume a
workflow automatically.

Before production rollout, qualify shared journal deployment, multi-host storage
and network failure, provider credential limits, sustained load and alerting.
Controlled single-host tests are not production reliability certification.
