> Updated release: [verified aggregate percentages](../verified-aggregate-percentages/deployment.md) retains the scoped query safeguards.

# Hosted scoped query model output — 10 November 2026

Deployed to **https://praxi.bellcorpstudio.com/app**.

- Release: `scoped-query-20261110-ce2917824f4b`.
- Source manifest SHA-256: `ce2917824f4ba4efbbdd4ee75fa8870648821559a1821780799efd81f45259cb`.
- Activated: 10 November 2026, 23:46:59 India time (18:16:59 UTC).
- Runtime files: crew.py, action_plans.py and graph.py.
- Frontend remains `6HEPrM8Si3RgcL39HkXgV`; no configuration or frontend change.

The model response schema now couples a base dataset with its projected fields for
bounded no-relationship catalogues. Valid aggregates and clarification remain allowed.
Larger catalogues and catalogues with relationships retain their previous contract.
Typed source validation remains mandatory. The model's correction receives the trusted
validator's exact rule, and bounded rejection diagnostics are persisted for both failed
attempts. No rejected raw model output or source rows are added to these diagnostics.

The saved screenshot run failed before source execution after exhausting its two model
attempts. Its rejected queries and exact rule were not previously stored, so this
release does not claim a reconstructed root cause. It addresses the weak schema and
feedback boundary and makes any future invalid output diagnosable. It does not grant
unlimited retries, silently drop invalid fields or guarantee every model response.

Validation: **41 regression tests passed**, plus **12 grouped-query/caveat compatibility
checks**. The final regression includes persistent rejection diagnostics, bounded
correction, no provider call after invalid outputs, independent worker progress,
existing query clarification and email planning. Canonical schemas, generated UI
contracts, strict OpenSpec and diff checks passed. Copied-account rehearsal used the
actual failed run's reviewed catalogue with controlled valid and invalid projections;
source ownership and precise feedback checks passed without networking or workers.
See [verification](verification.md) for qualification limits.

Private release evidence is retained in `.local/scoped-query-output-20261110/`:
fresh consistent tenant backups passing quick_check, current protected-table counts,
configuration copies and hashes, prior runtime source, source manifest, automation
snapshots and copied-account rehearsal. The retained verified full operator snapshot
remains separate. Actual in-flight work and near-due schedules were checked before
restarting the existing backend/tenant services and shared worker. No database was
restored or destructively migrated.

Authenticated public HTTPS checks passed for all three accounts: sessions, Workflows,
Data Intelligence, query configuration, query-tool registration and worker health.
Login returned 200; unauthenticated app/API returned 307/401. All five services are
active with zero automatic restarts. Protected histories, encrypted source/Google
credentials, configuration hashes and all saved automation documents are preserved.
No paid live model, source query, email, Sheets or Calendar action was performed for
verification. Existing two-slot runtime capacity and delivery approvals remain.

Refresh and generate a new workflow from the original prompt. Failed historical runs
are preserved rather than automatically rerun. Application-only rollback:

```
.venv-integrations/bin/python .local/scoped-query-output-20261110/release_control.py rollback
```

Rollback restores the three pre-change runtime files and restarts backend/tenant
services and worker. Databases, configuration and frontend are not restored.
