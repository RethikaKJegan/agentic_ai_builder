# Nonblocking execution response — 7 November 2026

**Confirmed HTTP execution/rediscovery defects fixed; dedicated Simpsons rollout
active. The user's existing execution completed and was not replayed.**

## Observed outcome and cause

The user reported `API_TIMEOUT` for request/correlation
`7824ef5e-9625-45fe-acc0-93c584d3019d`. Read-only tenant inspection found the matching
complaint/inspection/email-preparation workflow's durable run
`run_965172a4784e4c218a48d51ed39c7d8a` already **completed**, with complaint retrieval,
inspection retrieval, comparison and email preparation completed. The screenshot's
waiting state was not authoritative evidence of an unstarted run.

Two source defects explain the behavior:

1. `create_configured_app` deferred HTTP execution only for an API-only role.
   Combined mode already hosts a RuntimeWorker but advanced model/tool work inside
   HTTP execution and approval-continuation requests. This can exceed the existing
   30-second normal proxy timeout after the durable run has already been accepted.
2. The composition projection loaded execution only if the browser supplied its
   run ID. Losing the execute response lost that ID, so subsequent read-only plan
   polling could show pending tasks despite the persisted completed execution.

`workflow_api/live_providers.py` now uses the existing background-execution path
for API and combined roles. Durable admission returns the run promptly, while the
existing runtime worker performs execution with unchanged leases, permissions,
limits and approval checks. No larger proxy timeout or automatic replay is added.

`workflow_api/composition_presentation.py` now discovers the latest run for the
exact current workspace, subject and workflow when no explicit run is supplied.
It then uses the existing runtime loader and subject/workflow checks. Explicit run
selection remains scoped. This is read-only reconciliation, not run creation.

## Verification

Both added regressions failed before the implementation fix:
`/tmp/nonblocking-before.log`: **2 failed**, 17.42 seconds. The corrected focused
run `/tmp/nonblocking-focused.log`: **2 passed, 0 failed, 0 skipped**, 19.52 seconds.
The configuration regression forbids inline advancement and confirms a runtime
worker is configured. The projection regression compares implicit/explicit run
views and asserts no new runs or source reads.

Full affected modules are `tests/test_distributed_configuration.py`,
`tests/test_composition_presentation.py`, `tests/test_phase2_workers.py`, and
`tests/test_live_providers.py`, using the existing isolated fixtures and controlled
model/provider responses. Log `/tmp/nonblocking-qualified.log`: **71 passed,
0 failed, 0 skipped**, 250 warnings, 234.84 seconds. Focused/overlapping counts
are not summed as distinct coverage.

An isolated copy of the tenant store was initialized with an audit hook forbidding
all other SQLite connections and network calls. Startup required **zero new,
changed or removed schema objects**, zero network calls and no worker start.
See `evidence/startup-check.json`. This does not establish production backup/RPO.

Read-only metadata showed no queued/running tenant jobs or executions before
restarting only `agentic-builder-simpsons.service`. No schema migration, credential
change, operator/Subway restart, paid model test or external action was performed.
A first smoke-report formatter used the wrong task key after successful HTTP/run
assertions; only that formatter was corrected, then read-only GET verification
repeated without another restart or execution.

After rollout, an authenticated session GET confirmed `client-isolated` mode.
The composition view without a run ID returned the original completed run and
four completed task states. **Zero execute requests, model calls, source reads or
external actions** were submitted by this verification. Exact evidence is
`evidence/live-rediscovery.json`. No claim that an email was sent is made by an
email-preparation task or by this inspection.

Contracts, whitespace, strict scoped OpenSpec and regenerated SQL inventory drift
checks pass. Inventory now contains **1,193 calls and 123 literal tables**; the
added SELECT and line shifts are inventory changes, not a database migration or
universal PostgreSQL qualification.

The user should refresh/reopen the existing report, not create another execution.
Future configured combined-mode runs use existing background admission. Genuine
transport/storage failures may still produce unknown outcomes; immutable identities,
read-only state reconciliation and explicit approval requirements remain necessary.
This fix does not establish production readiness or close earlier external/audit
qualification blockers.
