> Updated release: [query validation and worker lease correction](../query-projection-worker-release/deployment.md) retains this approval-routing correction.

# Hosted execution-approval routing correction — 10 November 2026

Deployed to **https://praxi.bellcorpstudio.com/app**.

- Release: `execution-approval-20261110-c86221afff7e`.
- Source manifest SHA-256: `c86221afff7ecfc4736a5b3bce94f92a4ea1fa83f629ab394a156805fe5500dc`.
- Activated: 10 November 2026, 22:51:52 India time (17:21:52 UTC).
- Backend changes: `workflow_api/overview_automation.py` and `planning_defaults.py`.
- Frontend remains `6HEPrM8Si3RgcL39HkXgV`; no frontend build/swap or configuration change.

Clear execution-approval notices no longer block automatic workflow generation in
question-free mode. This applies to email, spreadsheet creation/update, Calendar,
web search and combined-tool intent. Existing workflow review, action approvals,
connector permissions and input validation remain authoritative. Real unresolved
inputs, unavailable access and ambiguous requirements still block supported execution.

Refresh Overview and generate a new request with the original short prompt. Older
blocked results retain their idempotent historical result. This release does not
rerun or rewrite them, execute provider actions, or add unavailable capabilities.

Validation: **145 backend tests passed**, covering the exact reported approval-only
route, mixed genuine gaps, normal action compilation with approval gates, tool
composition, Sheets/email delivery receipts, Calendar time authority and web research
provenance using controlled providers. Canonical schemas, generated UI contracts,
strict OpenSpec validation and diff checks passed. An isolated replay of the actual
saved faulty route against a copied Simpson store prepared successfully; a real
unknown-recipient requirement remained unresolved. No paid model or live provider
call was used for verification. See [verification](verification.md) for limits.

Private rollback source, fresh online tenant snapshots passing quick_check, scoped
configuration snapshots, current protected-table counts and automation snapshots are
retained at `.local/execution-approval-routing-20261110/`. The existing verified full
operator snapshot is retained separately. In-flight jobs and near-due schedules were
gated before restarting the existing backend/tenant services and shared worker.
No database was restored or destructively migrated.

Authenticated public HTTPS checks passed for operator, Simpsons and Subway: sessions,
Workflows, Data Intelligence, query configuration, registered query tools and worker
health. Public login returned 200 and unauthenticated app/API returned 307/401. All
five services are active with zero automatic restarts. Existing protected-history
counts, encrypted Google/source credentials, configuration-file hashes and all saved
automation documents were preserved. Verification sent no live emails, created no
spreadsheet/event and did not activate any schedule.

Application-only backend rollback:

```
.venv-integrations/bin/python .local/execution-approval-routing-20261110/release_control.py rollback
```

Rollback restores only the two pre-change source files and restarts the existing
backend/tenant services and worker. It does not restore databases or frontend artifacts.
