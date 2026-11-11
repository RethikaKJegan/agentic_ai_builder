> Latest release: [question-free workflows](../question-free-workflows/deployment.md) includes this immediate-work default.

# Hosted immediate-work default — 10 November 2026

Deployed to **https://praxi.bellcorpstudio.com/app**.

- Release: `immediate-default-20261110-6e8a3a832db1`.
- Source manifest SHA-256: `6e8a3a832db1f6bcd2aa244093eba4be66d144853237ce303fc7f21d37ecdb1a`.
- Activated: 10 November 2026, 22:00:10 India time (16:30:10 UTC).
- Backend changes: `workflow_api/overview_automation.py` and `planning_defaults.py`.
- Frontend remains `oyDtV0TfweDoMGSpb6VrX`, including automatic Workflows navigation.

Requests without execution timing prepare immediate work rather than an empty
future timer. Explicit schedules remain scheduled. Immediate readiness does not
skip workflow review or email approval. Refresh Overview and generate a new request;
historical clarification results and existing schedules are preserved.

Fresh online tenant backups passed quick_check; the verified operator snapshot
from 11:28:20 UTC remains retained. Current history counts, configuration copies,
prior source files and automation-document hashes were recorded. Actual running
work and schedules due within five minutes were gated before restarting the
existing backend/tenant services and shared worker. The frontend was not restarted
or replaced. No database migration, restoration or configuration change was made.

See [verification](verification.md) for the regression and controlled replay evidence.
Application-only rollback:

```
.venv-integrations/bin/python .local/immediate-workflow-default-20261110/release_control.py rollback
```

This restores the two prior backend source files and restarts backend services/the
worker through the same safe restart gates. It does not restore databases or edit
schedules, credentials or the frontend.

Post-deployment authenticated HTTPS checks passed for all three accounts. All five
services are active with zero automatic restarts. Existing history counts, encrypted
credentials and configuration are preserved (generated Registry metadata excluded).
Every existing automation document matches its pre-activation hash.
