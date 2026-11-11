# Hosted composed-intent correction — 10 November 2026

Deployed to **https://praxi.bellcorpstudio.com/app**.

- Release: `composed-intent-20261110-ac3bd3d04357`.
- Source manifest SHA-256: `ac3bd3d04357e63d7df69b45ac4c6d6c261356e13a243313b5207363b85ad01b`.
- Activated: 10 November 2026, 21:28:01 India time (15:58:01 UTC).
- Only backend router source `workflow_api/overview_automation.py` changed.
- Existing frontend build retained: `EiDLCCE7beRH3coeDHj3o`.

Analysis plus email/Sheets/Calendar actions no longer fails merely because a
schema-valid interpreter response used population/investigation as its category.
The server derives the composed category from the existing actions and recurrence.
It does not introduce actions or override negative instructions or approvals.
Refresh Overview and generate a new workflow using the original short prompt.
Historical failed jobs remain unchanged.

Fresh online tenant backups passed quick_check; the verified operator snapshot
from 11:28:20 UTC remains retained. Current counts, fresh configuration/credential
copies and the prior router source were saved. No running work or schedule due
within five minutes was allowed during activation. Existing future schedules and
authorizations were recorded for exact post-deployment preservation comparison.
Only backend/tenant services and the shared worker were restarted. No database,
frontend or configuration replacement and no destructive migration was performed.

See [verification](verification.md) for tests and controlled-model limitations.
Application-only rollback:

```
.venv-integrations/bin/python .local/composed-intent-fix-20261110/release_control.py rollback
```

Rollback restores only the saved router source and restarts backend services and
the worker after the same quiescence gates. It does not restore databases or change
existing schedules, credentials or the frontend.

Post-deployment authenticated HTTPS checks passed for all three accounts. All five
services are active with zero automatic restarts. History counts and encrypted
credentials/configuration are preserved (generated Registry metadata excluded).
All existing automation record documents match their pre-activation hashes.
