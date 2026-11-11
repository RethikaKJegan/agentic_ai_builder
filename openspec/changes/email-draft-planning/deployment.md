> Updated release: [scoped query model output](../scoped-query-output/deployment.md) retains the generic email planning correction.

# Hosted generic email planning correction — 10 November 2026

Deployed to **https://praxi.bellcorpstudio.com/app**.

- Release: `mail-planning-20261110-a13b9929c6de`.
- Source manifest SHA-256: `a13b9929c6deab55b69378f63b9a523765c2047e91f095f18be63f14d3cfa806`.
- Activated: 10 November 2026, 23:38:17 India time (18:08:17 UTC).
- Backend changes: overview_automation.py, planning_defaults.py and action_plans.py.
- Frontend remains `6HEPrM8Si3RgcL39HkXgV`; no frontend rebuild/swap or configuration change.

Supported-route interpretation concerns now pass to action planning as context.
Actual typed action inputs, source authority, schedule validation and approval gates
remain the executable prerequisites. Sampling caveats and preliminary-review limits
must not independently prevent a supported draft. Unsupported/ambiguous/event routes
retain their blocking behavior. No symptom, dataset, customer or email value is hardcoded.

New route responses classify recipient_mode separately from any address. For selected
account delivery, preparation reads the destination from the scoped owned connection;
explicit supplied recipients take precedence and unresolved named third parties remain
unresolved. Plain email drafting prepares text without inventing a recipient or mailbox
write. Explicit mailbox persistence keeps its connector prerequisites and approvals.
Refresh Overview and generate a new workflow; old blocked results retain their history.

Validation: **104 regression tests passed**, plus **7 focused checks** (overlapping
cases; not 111 unique tests), including structured model transport, cross-domain goals,
selected-account delivery, explicit-recipient precedence, unknown third-party handling,
no-recipient draft content and preserved action approvals. Canonical contract schemas,
generated UI contracts, strict OpenSpec and diff checks passed. Copied-account replay
of both saved faulty route concerns passes intent preparation with controlled new
recipient modes. No live paid model, source query, email or mailbox write was used.
See [verification](verification.md) for scope and limits; arbitrary model output cannot
be guaranteed valid, and genuine missing execution inputs still block safely.

Private backups/evidence are retained under `.local/email-draft-planning-20261110/`:
fresh consistent tenant snapshots passing quick_check, current protected-table counts,
configuration copies/hashes, prior source and release manifests, automation snapshots
and isolated replay. The verified full operator snapshot remains retained separately.
Actual in-flight jobs and near-due schedules were gated before restarting the existing
backend/tenant services and worker. No database was restored or destructively migrated.

Authenticated public HTTPS checks passed for operator, Simpsons and Subway: session,
Workflows, Data Intelligence, query configuration, query tool registration and worker
health. Login returned 200, unauthenticated app/API returned 307/401. All five services
are active with zero automatic restarts. Existing protected-history counts, encrypted
Google/source credentials, configuration hashes and all automation documents were
preserved. Prior two-slot runtime capacity and query validation correction remain.

Application-only rollback:

```
.venv-integrations/bin/python .local/email-draft-planning-20261110/release_control.py rollback
```

Rollback restores only the three pre-change backend files and restarts the existing
backend/tenant services and worker; databases, configuration and frontend remain intact.
