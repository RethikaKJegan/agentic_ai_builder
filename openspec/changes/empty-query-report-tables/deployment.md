# Hosted empty-query report tables — 11 November 2026

Deployed to **https://praxi.bellcorpstudio.com/app**.

- Release: `empty-report-20261111-cb5425fdfdac`.
- Source manifest SHA-256: `cb5425fdfdac0052a6445ab7e92d57d74f90634cbae20d55bc230b996d21dd0c`.
- Activated: 11 November 2026, 12:22:07 India time (06:52:07 UTC).
- Runtime: new report_tables.py; updated action_plans.py and crew.py.
- Frontend remains `6HEPrM8Si3RgcL39HkXgV`; no frontend or configuration change.

The actual failure occurred after a successful complete zero-match query. Generated
spreadsheet tabs contained rows=[], violating the pinned sheet tool's minimum-one-row
contract. The correction supplies trusted downstream table constraints and complete
empty-result context to content preparation. Empty generated tables become explicitly
labelled report-status tables before persistence/approval, without invented status
groups, counts per group or average HMR values. Nonempty tables remain unchanged.

Table validation now occurs at content generation, using the actual downstream tool
schema. Header uniqueness, width, scalar cells, source references and URL checks remain.
No query, permission, approval gate or external effect identity is changed. Mixed,
incomplete or unverified query evidence cannot be represented as a complete no-match
report. Invalid unrelated content still stops safely; this is not an unlimited-retry
or all-future-model-output guarantee.

Validation: **78 regression tests passed**, plus **8 focused checks** (overlapping
cases; not 86 unique tests). The regression includes zero-match query→report→sheet→
email delivery through controlled providers and verified receipts, normal nonempty
query delivery, Calendar authority, web research, aggregate percentages and connector
safety. Focused checks cover incomplete/unverified/mixed evidence, early table errors,
provider table-schema limits and unchanged canonical schemas. Actual copied failed
report tabs fail the original pinned schema and pass after normalization, preserving
summary and citations. Canonical contracts, generated UI contracts, strict OpenSpec
and diff checks passed. See [verification](verification.md) for scope and limits.

Private safeguards at `.local/empty-query-report-tables-20261111/` include fresh online
tenant backups passing quick_check, current protected-table counts, configuration
copies/hashes, pre-change source, source manifest, automation snapshots and copied-run
replay. The verified full operator snapshot remains separately retained. Actual running
work and near-due schedules were gated before restarting existing backend/tenant services
and shared worker. No database was restored or destructively migrated.

Authenticated public HTTPS checks passed for operator, Simpsons and Subway: sessions,
Workflows, Data Intelligence, query configuration, query-tool registration and worker
health. Login returned 200; unauthenticated app/API returned 307/401. All five services
are active with zero automatic restarts. Protected-history counts, encrypted Google/
source credentials, configuration hashes and all existing automation documents were
preserved. No live model/source query, email, spreadsheet or Calendar write was used
for verification. Existing failed runs and artifacts were not replayed or edited.

Generate a new workflow from the original prompt to use the corrected content path.
Application-only rollback:

```
.venv-integrations/bin/python .local/empty-query-report-tables-20261111/release_control.py rollback
```

Rollback restores the two modified runtime files, removes the new report-table module
and restarts backend/tenant services and worker. Databases, configuration and frontend
are not restored.
