> Updated release: [empty-query report tables](../empty-query-report-tables/deployment.md) retains the deterministic percentage calculation.

# Hosted verified aggregate percentages — 11 November 2026

Deployed to **https://praxi.bellcorpstudio.com/app**.

- Release: `aggregate-percent-20261111-19ec7bd63922`.
- Source manifest SHA-256: `19ec7bd639220287433c5025387ffa0c52094f6efd4a1abc082309ed8a24493b`.
- Activated: 11 November 2026, 11:37:31 India time (06:07:31 UTC).
- Runtime: new aggregate_math.py; updated action_plans.py and crew.py.
- API: updated workflow_api/action_plans.py content/planning guidance.
- Frontend remains `6HEPrM8Si3RgcL39HkXgV`; no frontend or configuration change.

Content steps now receive deterministic percentage evidence from verified, compatible,
complete count(*) query dependencies. Report/spreadsheet guidance allows these supplied
values and preserves the prohibition on calculating population totals from displayed
sample rows. Numerator/denominator query references, filters and source/account scope
accompany the rounded percentage. Zero totals are undefined, and incompatible or
incomplete evidence yields no derived metric. No new external tool or permission is
introduced. Existing query validation, delivery approvals and two runtime slots remain.

The actual saved counts replay to **1,588 / 5,810 × 100 = 27.33%**, using Decimal
arithmetic without model computation, source calls or provider writes. Historical
reports and existing Google Sheets are preserved; generate a new workflow to obtain
new content. This release does not silently rewrite previously created artifacts.

Verification: **71 regression tests passed**, plus **28 focused percentage/grouped-query
and caveat checks** (overlapping cases, not 99 unique tests). Coverage includes complete
query-to-Sheets/email workflows, Calendar authority, web-research provenance, numerator/
denominator scope, zero totals, large counts, incompleteness and deterministic content
input. Canonical schemas, generated UI contracts, strict OpenSpec and diff checks passed.
See [verification](verification.md) for conservative derivation rules and limits.

Private release evidence at `.local/verified-aggregate-percentages-20261111/` includes
fresh consistent tenant snapshots passing quick_check, current protected-table counts,
configuration copies/hashes, pre-change source, source manifest, automation snapshots
and replay of actual receipts from the copied Simpson store. The verified full operator
snapshot is retained separately. Actual in-flight work and near-due schedules were
gated before restarting existing backend/tenant services and shared worker. No database
was restored or destructively migrated. Only disposable isolated build caches from
older rehearsals were removed to provide space; release artifacts and backups remain.

Authenticated HTTPS checks passed for all three accounts: sessions, Workflows, Data
Intelligence, query configuration, query registration and worker health. Login returned
200, and unauthenticated app/API returned 307/401. All five services are active with zero
automatic restarts. Protected-history counts, encrypted Google/source credentials,
configuration hashes and all existing automation documents were preserved. Verification
did not call live paid models, execute source queries, or write email/Sheets/Calendar.

Application-only rollback:

```
.venv-integrations/bin/python .local/verified-aggregate-percentages-20261111/release_control.py rollback
```

Rollback restores three modified files, removes the new aggregate-math module and
restarts backend/tenant services and worker. Databases, configuration and frontend
are not restored.
