# Hosted short-prompt defaults — 10 November 2026

Deployed to **https://praxi.bellcorpstudio.com/app**.

- Release: `short-prompt-20261110-5bc80aa0db8d`.
- Source manifest SHA-256: `5bc80aa0db8d7421ae990d2df66ff86bc30ffb15937d44f966a77c2e5545c96b`.
- Activated: 10 November 2026, 17:39:31 India time (12:09:31 UTC).
- Frontend remains `EiDLCCE7beRH3coeDHj3o`.
- Backend modules: `planning_defaults.py`, `goal_inputs.py`,
  `overview_automation.py`, `data_queries.py` and `action_plans.py`.

Short summaries use declared report defaults and existing workspace permissions.
Explicit self-mail uses the selected owner-scoped account before interpretation.
Existing source, query, Registry, account and execution-approval checks remain.
Start a new generation after refreshing Overview; historical clarification results
remain unchanged and are not retried automatically.

Fresh online Simpson/Subway backups passed quick_check; the verified operator
full snapshot from 11:28:20 UTC is retained. Current history counts and fresh
configuration/credential copies were recorded before activation. Exact previous
source files were retained for rollback. No active run, job or schedule was present
at activation gates. Only existing backend/tenant services and the shared worker
were restarted; no frontend/configuration replacement, migration or database
restoration was performed.

See [verification](verification.md) for the 156-test suite and copied-account
validation limits. Deployment verification uses authenticated read-only HTTPS
checks across all three account routes and history/credential comparisons, without
submitting workflows or invoking paid models or provider writes.

Application-only rollback:

```
.venv-integrations/bin/python .local/short-prompt-defaults-20261110/release_control.py rollback
```

This restores the four prior source files, removes the added defaults module and
restarts backend services/the worker. It does not restore databases or the frontend.

Post-deployment checks passed for all three accounts. All five services are active
with zero automatic restarts. Existing history counts, encrypted Google/source
credentials and configuration hashes are preserved (generated Registry metadata
excluded). The original clarification job result is unchanged.
