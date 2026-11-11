> Updated release: [generic email planning correction](../email-draft-planning/deployment.md) retains these query-validation and worker-capacity fixes.

# Hosted query validation and worker lease correction — 10 November 2026

Deployed to **https://praxi.bellcorpstudio.com/app**.

- Release: `query-worker-20261110-957b64db5e4f`.
- Source manifest SHA-256: `957b64db5e4f19429ff699f3893314d8b2a84969e93a8dc83603ba3c565bb1a4`.
- Activated: 10 November 2026, 23:07:19 India time (17:37:19 UTC).
- Frontend remains `6HEPrM8Si3RgcL39HkXgV`; no frontend rebuild or swap.
- Backend files: data_queries.py, action_plans.py, live_providers.py, runtime/action_plans.py
  and runtime/graph.py.
- Enabled `BUILDER_WORKER_CONCURRENCY=2` for operator, Simpsons and Subway, preserving
  active-standby supervisor mode and all other configuration values.

New automatic query workflows include a reviewable allowance for one model correction.
Generated queries validate before source invocation. Finished worker calls relinquish
only their own stopped execution lease. Each account has two runtime execution slots;
new work can progress alongside one active workflow. Capacity remains bounded and
active work is not cancelled, overwritten or preempted. No latest-first queue-priority
claim is made. Refresh Overview and generate a new workflow from the original prompt;
failed historical executions and their reviewed budgets are preserved.

Private release evidence is under `.local/query-projection-worker-release-20261110/`:
fresh consistent tenant snapshots passing quick_check, current protected-table counts,
configuration copies/hashes, pre-change source, source manifest, automation snapshots
and copied-account replay. The existing verified full operator snapshot remains
retained separately. Actual in-flight work and near-due schedules were gated before
restarting existing backend/tenant services and the shared worker. No database was
restored or destructively migrated.

Post-activation public HTTPS checks passed for all three scoped accounts: session,
Workflows, Data Intelligence, query configuration, query registration and worker health.
Login returned 200; unauthenticated app/API returned 307/401. Runtime component health
records show capacity=2 in each account. All five services are active with zero automatic
restarts. Existing protected-history counts, encrypted Google/source credentials,
configuration outside the authorized concurrency setting and all automation documents
were preserved. Verification triggered no paid model or external provider action.

See [verification](verification.md) for test counts and limits. Application-only rollback:

```
.venv-integrations/bin/python .local/query-projection-worker-release-20261110/release_control.py rollback
```

Rollback restores the five pre-change source files and prior concurrency setting,
then restarts backend/tenant services and worker. Databases and frontend stay intact.
