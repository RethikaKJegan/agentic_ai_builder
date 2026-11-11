> Updated release: [execution-approval routing correction](../execution-approval-routing/deployment.md) prevents ordinary approval notices from blocking preparation.

# Hosted question-free workflows — 10 November 2026

Deployed to **https://praxi.bellcorpstudio.com/app**.

- Release: `question-free-20261110-69a3569eb75f`.
- Source manifest SHA-256: `69a3569eb75fd4b9fc257e548a78584ad56faf10675e24abd04e21c965f91708`.
- Frontend build: `6HEPrM8Si3RgcL39HkXgV`; prior: `oyDtV0TfweDoMGSpb6VrX`.
- Activated: 10 November 2026, 22:32:14 India time (17:02:14 UTC).
- Enabled `BUILDER_QUESTION_FREE_WORKFLOWS=1` for operator, Simpsons and Subway.
  Other existing configuration values and credentials are preserved.

Refresh Overview and generate a **new** workflow from the short request. Supported
work uses available context and defaults without follow-up questions. Unresolved
requests create visibly blocked drafts with limitations instead of questionnaires.
Required action review/approvals remain. Existing saved results and schedules were
not rewritten or rerun. This behavior does not supply missing query capabilities or
confirm a diagnosis without supporting evidence.

Private release safeguards are retained under
`.local/question-free-workflows-20261110/`: fresh online tenant backups passing
quick_check, configuration copies and hashes, pre-change source files, source and
frontend manifests, automation snapshots and isolated rehearsal evidence. The
previously verified complete operator snapshot from 11:28:20 UTC remains retained;
current operator protected-table counts were separately captured before activation.
No database was restored or destructively migrated.

Actual in-flight work and schedules due within five minutes were checked before
restarting the existing backend/tenant services, worker and frontend. The exact
verified frontend artifact replaced the prior artifact; old static chunks were
retained for existing browser tabs. All five services are active with zero automatic
restarts after activation.

Authenticated public HTTPS checks passed for all three scoped accounts: session,
Workflows page, Data Intelligence, query configuration, registered query tool and
worker health. Public login returned 200; unauthenticated app/API returned 307/401.
Protected history counts, existing encrypted source/Google credentials, configuration
values outside the one authorized setting and all existing automation documents
were preserved. Six hosted desktop/mobile browser journeys passed across the three accounts,
with zero page errors or API mutations. The Simpsons check opened and refreshed
a current completed investigation. An older verification target correctly returned
WORKFLOW_DELETED and was not restored. Private release evidence records both. Verification did not generate a live workflow, call a paid model or perform
email, spreadsheet, calendar or other external writes.

See [verification](verification.md) for test coverage and qualification limits.
Application-only rollback, including the one added setting and prior artifact:

```
.venv-integrations/bin/python .local/question-free-workflows-20261110/release_control.py rollback
```

It restores the pre-change application source/artifact and previous question-free
setting; it does not restore databases or provider journals.
