# Data Intelligence Phase 6: durable query jobs

The Questions UI now submits read-only execution as an owned background job when
the server advertises `jobs_available`. It polls observed stages, supports cancel,
restores recent owned jobs after navigation/refresh and retrieves only complete
unexpired results. Planning is still metadata-only; the reviewed logical plan and
all Phase 4/5 arithmetic, relationship, source and transfer checks remain.

## API and ownership

- `POST /data-queries/jobs`, body `{ "plan_id": "..." }`, requires an
  `Idempotency-Key` containing 8–128 letters/digits/underscores/hyphens. Returns
  HTTP 202 with the owned job. Retrying the same owner/key/plan returns that job;
  changing the plan under the same retained key returns 409.
- `GET /data-queries/jobs` returns at most twenty recent owned jobs.
- `GET /data-queries/jobs/{job_id}` returns metadata/progress, never result rows.
- `POST /data-queries/jobs/{job_id}/cancel` records cancellation intent. Already
  completed jobs keep their terminal state; queued jobs cancel immediately.
- `GET /data-queries/jobs/{job_id}/result` returns a complete unexpired result.
  Missing completion returns 409; expired result returns 410.

All routes use the existing session and no-store API envelope. Both `tools.read`
and `tools.assign` are required for submit/status/list/cancel/result. Ownership is
workspace plus subject, not possession of a job ID. Workers resolve current
server authority; jobs never store permissions, credentials or caller auth
snapshots. This deployment uses the existing server-configured development
identity/roles; Phase 6 does not introduce production multiuser IAM or a new login
system. Other authority providers must supply an equivalent current resolver.

The versioned `shared/contracts/data-sources/query-jobs-v1.schema.json` defines
states, metadata/progress and result references. The query status response gains
optional capability/time/retention fields. Existing query and new job contracts
also allow the optional correlation/version metadata supplied by the canonical
HTTP envelope. Workflow/agent/tool contracts are unchanged; no contributor
acceptance or external notification is inferred.

## Durable execution and recovery

`data_query_jobs` lives in the configured WorkflowStore. SQLite write transactions
and PostgreSQL's existing advisory-serialized write transaction boundary protect
admission, claims and publication. Submission pins an immutable server-owned copy
of the reviewed saved plan and graph fingerprint, so ordinary latest-twenty plan
pruning does not destroy queued work. Plan expiry and current graph/source access
are rechecked before executing. A pinned copy does not extend plan validity.

States are queued, validating, running, finalizing, succeeded, failed,
cancel_requested and cancelled. Four worker threads can claim jobs, with at most
four valid active claims globally and one per workspace/owner, across independent
coordinators. A random attempt token fences each claim; its 15-second lease is
renewed once per second. A hard-crashed or interrupted attempt may restart once,
within the original deadline and plan validity. Partial data/snapshots are always
discarded. Recovery uses fresh database reads and never mixes attempts. Ordinary
source, arithmetic or relationship errors are not automatically retried.

The execution control is request-local and applies to optimized PostgreSQL,
MongoDB, federation and bounded fallback. Progress reports real stages and completed
fragment/transfer counts, never guessed percentages. The independent monitor can
observe cancellation, lost authority and lost coordination while a statement is
blocked. PostgreSQL cancellation uses the driver's bounded `cancel_safe` against
that attempt's tracked connection. MongoDB cancellation remains cooperative around
existing bounded operations; no privileged server-wide kill command is used.
Cancellation is not guaranteed instantaneous.

Graceful worker shutdown stops new claims and interrupts current attempts. An
interrupted attempt is requeued at most once after cleanup, if still valid. Hard
crashes recover after lease expiry. Stale attempts cannot publish. During lease
loss an old database operation can briefly overlap cleanup/recovery; source
operation timeouts still bound it. Four active claims are a coordination limit,
not a claim of instantaneous global termination of partitioned database reads.

Publication validates the result contract and whole-response size, encrypts the
complete payload, and checks current authority, token, lease, deadline,
cancellation and graph freshness in the serialized publication boundary. A review
or source change committed before publication prevents success. A cancellation
committed before publication wins; success already committed before a cancel
request remains success. Failures/cancellations expose no partial result.

## Budgets and retention

Default deadline is 180 seconds FROM SUBMISSION, including queue/recovery time.
`BUILDER_DATA_QUERY_JOB_TIMEOUT_SECONDS` may configure 45–300 seconds; invalid
configuration fails startup. Effective execution also ends at plan expiry. Neither
heartbeat nor recovery resets the deadline. Existing database statement timeouts
(up to ten seconds), source memory/type/precision bounds, one-million-row fact
budget, four datasets, 5,000-row dimensions/intermediates, 500 returned rows and
2 MB data transfer/output limits remain. Background execution does not authorize
an arbitrarily long SQL statement or a larger dataset. The complete stored result
envelope is additionally limited to 2.5 MB, including evidence.

Admission allows at most five unfinished jobs per owner, twenty per workspace and
one hundred globally. Live encrypted results are capped at twenty per owner and
one hundred globally, checked at submission AND publication. These are background
job limits. The legacy synchronous execute API remains compatible with its original
45-second budget and existing process-local concurrency guard; the current UI
uses jobs against an upgraded server.

Results are encrypted with the existing persistent data-source Fernet cipher and
retained for 15 minutes after completion. API and worker must share that persistent
key. Status/list do not decrypt results. Retrieval rechecks current permissions,
source/relationship context and result expiry; an old successful plan's execution
TTL does not itself prevent retrieval during the result window. A changed context
can prevent access even before the result expires.

Worker maintenance and API access remove expired ciphertext logically from the
job row. Job success metadata remains, with `result_available=false`, until its
24-hour metadata retention ends. Cleanup also runs while the queue is idle. If all
workers/API access are stopped, physical cleanup waits until service resumes;
expiry still prevents retrieval. This is not a claim of secure physical erasure
from database backups/WAL. Job IDs/idempotency records are retained with metadata
for up to 24 hours. Query rows are not stored in plaintext history, logs or browser
storage, and are never sent to the planning model. The UI clears expired results
and rejects result responses arriving after their displayed retention window.

## Worker integration

The existing `DataQueryJobs` component joins the builder worker supervisor.
`scripts/run_builder_worker.py` runs it in worker mode; API-only mode does not
start a consumer. A combined development app starts consumers through the existing
startup lifecycle. API restarts do not discard queued jobs or encrypted results.
The worker needs the same configured store and data-source key as the API.

## Verification

Run backend tests against an isolated PostgreSQL database whose test owner can
create/drop schemas. The engine fixtures launch a temporary MongoDB replica set
on loopback port 27249:

```
BUILDER_TEST_POSTGRES_DSN=<isolated-test-database> .venv-integrations/bin/python -m pytest -q tests/test_data_query_jobs.py tests/test_data_query_pushdown.py tests/test_data_query_federation.py tests/test_data_queries.py tests/test_data_relationships.py tests/test_data_sources.py tests/test_phase2_workers.py
```

Frontend requires Node 22. Focused unit/domain checks use `npm run test --
src/features/data-sources/DataQuestions.test.tsx src/domain`. Production browser
checks use `QUERIES_FRONTEND_DIR=<isolated-production-build> npm run test:e2e --
--config playwright.queries.config.ts`. Browser fixtures test presentation and
refresh/cancel/expiry independently of real database lifecycle tests.

Verified and deployed on 2026-10-18:

- 178 backend tests passed, including isolated real PostgreSQL/MongoDB query
  equivalence, actual PostgreSQL statement cancellation, killed-process recovery,
  concurrent PostgreSQL-store claims, cancellation/publication races, authority
  changes, source/review freshness, queue/result capacity and encrypted expiry.
- 103 focused frontend/domain/proxy tests, TypeScript, scoped ESLint, production
  build, shared contracts, strict OpenSpec and whitespace checks passed. Ten
  production browser fixture scenarios covered legacy query review/results and
  background refresh/cancel/expiry on desktop/mobile. A production proxy test
  verifies exact forwarding of the new idempotency header and request body.
- Live public UI submitted a real model-planned federated job and recovered the
  same job after API restart/browser refresh without resubmission. All eight
  category sales sums and weighted averages over 2,155 order details and 77
  products matched independent PostgreSQL aggregation plus an eight-document
  MongoDB snapshot lookup. Progress reported three completed fragments / 24
  transferred records / 2,744 serialized bytes. Native execution took 12.775 s;
  this is execution time, not the entire queue/UI lifecycle.
- A second live owned job cancelled from an active attempt. Its result endpoint
  returned 409 and its stored result ciphertext was absent. The successful job's
  stored ciphertext decrypted to the verified result; status reads exposed no
  rows. Live desktop/mobile checks reported no page errors or horizontal overflow.
- Evidence: `.local/query-jobs-backend.log`, `.local/query-jobs-ui-tests.log`,
  `.local/query-jobs-browser.log`, `.local/query-jobs-build.log`, and
  `.local/query-jobs-phase6/public-jobs.json`. Raw live aggregate rows were removed
  from the Phase 6 JSON verification capture after comparing canonical hashes;
  evidence retains metadata/counts and equal actual/independent hashes.
- API/frontend/worker are active. Original frontend rollback artifact:
  `.local/ui-rollbacks/query-jobs-phase6-20261018/.next`. No connected cloud rows,
  credentials or relationship reviews were changed. Planning/job/audit records
  were created through normal authorized read-only execution. Worker hard-kill
  recovery was tested in isolation, not by killing the live production worker.

Broader legacy suites, production IAM and contributor acceptance are not claimed.
