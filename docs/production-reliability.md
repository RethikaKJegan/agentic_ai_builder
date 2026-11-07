# Production qualification and recovery

These are development changes and isolated test procedures. Deployment, live
provider actions, production migration and service restarts require separate
operator authorization. Multi-host/network partitions and hardware/storage faults
need a representative environment; single-host tests do not establish them.

## Capacity settings

Continue to use `BUILDER_WORKER_MODE=multi-active` and the Phase 2 server limits.
New trusted environment settings:

| Setting | Default | Scope |
| --- | --- | --- |
| `BUILDER_TOTAL_CONCURRENCY` | 128 | Live leased runtime runs in the shared workflow store |
| `BUILDER_ACCOUNT_RESERVED_CAPACITY` | `{}` | Account ID → protected slots, e.g. `{"subway":1}` |
| `BUILDER_SHARED_PROVIDER_RATE_LIMITS` | `{}` | Provider/bucket ID → requests per minute |
| `BUILDER_CREDENTIAL_BUCKETS` | `{}` | `provider:credential_reference` → shared bucket ID |

Reservations must fit the total and each account's existing concurrency limit.
Unused reserved slots remain protected from other accounts; they are not loaned
out. A server with insufficient resources should lower its configured total.
The run lease and current authority still govern execution and result acceptance.
These are logical runtime slots, not dedicated OS processes or CPU guarantees.

Map all aliases of the same credential to the same trusted bucket. For example,
`{"smtp:cred_simpson":"mail_shared","smtp:cred_subway":"mail_shared"}` with
`{"mail_shared":30}` limits both accounts together. Provider-wide limits are a
fallback when no credential bucket is configured. No credential reference or
secret is returned in the quota table: shared bucket keys are hashed.

Counters and protected capacity coordinate within one authoritative workflow
store. Dedicated client deployments using separate stores do not share those
counters. They must use separate credentials or an independently qualified
central quota authority/provider gateway before claiming a cross-store global
limit. This change does not introduce a distributed cross-database transaction.
Model/provider-wide limits cover calls through the existing runtime reservation
path; they do not claim to meter every unrelated planner or provider client.
Fixed-minute counters permit a boundary burst. Unknown calls are never refunded
on the assumption that the provider did nothing.

## Source synchronization

The existing singleton supervisor now also owns `KnowledgeSyncWorker` when unified
knowledge is enabled. It polls at most sixteen due projections per cycle, at a
30-second interval, using freshly authenticated owner authority. It reuses existing
bounded readers and semantic metadata; no CDC support is invented.

Changed package/preparation evidence creates a new immutable projection. A repeated
preparation read with identical evidence refreshes the existing pin, preserving
historical hash semantics. Source disconnection, deletion, denied authority or
refresh failure marks the current projection stale with bounded retry cadence.
No roles are reconstructed from saved documents. Changed semantic interpretations
keep their existing review status; polling never confirms an inference.

Running workflows retain their exact pins. Stale graph access blocks current
reasoning and existing source revalidation guards recovery. Use the current
preparation/review/replan flow to continue with changed evidence. There is no
silent repinning or automatic approval carryover across knowledge revisions.
Historical working/experience memory remains reference evidence and cannot
restore missing current source authority. This is bounded polling, not immediate
change notification or an uninterrupted multi-day freshness guarantee.

## Investigation UI

Workflow → Business Investigation already shows persisted dependencies, agents,
receipts, waits, approvals, tool results and scoped working memory. Its existing
knowledge inspector now shows bounded pinned account concepts/record references,
meaningful predicates, relationship status and current versus historical freshness.
The memory/recovery inspector shows the actual recovery summary and original
uncertain effect references. There is no blind replay control. Existing authorized
resume/cancel and exact-payload approval flows remain authoritative.

`GET /runs/{id}/knowledge` uses only the run's saved pins, current owner scope,
at most eight projections, 32 nodes/edges each, and omits source row values.
`GET /runs/{id}/recovery` retains its existing permission checks. Historical runs
without a graph pin display that absence. Read failures display unavailability,
not fabricated success. No model chain-of-thought is exposed.

## Operational alerts

`GET /operational-alerts` and `/worker-health` require current administrative
monitoring permission. Alert facts are workspace-scoped; worker/component health
is infrastructure status. No endpoint accepts a caller-supplied workspace.
Alerts include no workers, backlog ≥100, oldest queued age ≥300s, dead-letter
jobs, specific uncertain-effect failures, failed runs, stale knowledge, failed
components and recognized connector/model failures. These are deterministic
conditions over persisted state, not an external notification subscription.

Symptoms and actions:

- Database unavailable: retain original job/request/effect IDs, restore database
  connectivity, inspect workers and claims before retrying. Availability/connection
  failures include PostgreSQL administrator/crash shutdown states.
- Queue backlog: inspect account reservations, provider windows, worker heartbeat
  and delayed retries. Do not raise workflow budgets to clear an overloaded queue.
- Unknown provider outcome: inspect scoped recovery details and verify the remote
  provider plus original connector journal. A missing local receipt is not failure
  evidence. Existing report read-back is the supported verified reconciliation.
- Stale graph: restore source grants/metadata, perform a fresh authorized read,
  then review a new preparation. Preserve original knowledge and memory references.
- Model/citation failure: inspect the supported output schema and evidence refs.
  Execution completion and factual/business-task success remain separate.

Alert delivery, retention/acknowledgement policy, aggregation of process-local
metrics and environment SLOs require an operator-managed monitoring deployment.
No email/webhook/Slack messages are sent by these changes.

## Backup, restore, rollout and rollback

Use existing SQLite online `snapshot`/backup and the inventoried migration CLI;
do not copy a live database file without accounting for its journal/WAL. Back up
main application state and every auxiliary connector/case/resource store together
under quiesced writes or an independently proven consistent cut. Protect backups
with private filesystem permissions and encryption in the deployment's backup
system. The isolated tests use private test snapshots only.

For PostgreSQL, use a restricted backup role and `pg_dump`/`pg_restore` into an
isolated destination; validate schema, table counts/hashes, events, checkpoints,
approvals, waits, effect receipts, graph revisions and owner/tenant isolation.
Bring up an isolated worker with controlled transports, verify retained effect
identities, then qualify restoration under the actual deployment topology.
Do not restore an old connector receipt set while retaining newer workflow state.

Before authorized rollout: preserve exact source/build/config versions, take and
drill coordinated backups, validate migration contracts and shared-journal access,
qualify the intended database/provider/network failures and set measured SLOs.
Start with conservative server limits; monitor queue latency, errors and provider
windows. Rollback means restoring a compatible code/build/config version and a
reviewed consistent state set, not replaying effects from an earlier snapshot.
Neither deployment nor production restore is performed by this phase.
