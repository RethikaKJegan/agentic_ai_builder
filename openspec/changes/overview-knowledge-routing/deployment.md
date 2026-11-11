# Hosted knowledge-routing hotfix — 10 November 2026

Deployed to **https://praxi.bellcorpstudio.com/app**.

- Release: `knowledge-route-20261110-55967c539230`.
- Source manifest SHA-256: `55967c5392301ce3bfc7644201ec11eebc6cfac41381fae77c8ff7b48592fdce`.
- Activated: 10 November 2026, 17:03:51 India time (11:33:51 UTC).
- Existing frontend build retained: `EiDLCCE7beRH3coeDHj3o`.
- Changed backend modules: `overview_automation.py`, `action_plans.py` and
  `composition_presentation.py` under `workflow_api/`.

Knowledge-intent plans now consume pinned workspace knowledge through content
preparation and cannot substitute record queries. Refresh Overview and generate a
**new workflow** with the original prompt. Historical failed executions remain
unchanged; retrying the old query plan does not apply this correction.

Fresh consistent online backups of all three stores passed SQLite quick_check.
Fifty-three configuration/credential files and the exact prior three source files
were retained privately. No active runtime/job/schedule work was present at
activation gates. Existing backend/tenant services and the shared worker were
restarted through their systemd units. No frontend replacement, configuration
change, database restoration or destructive migration was performed.

All three account routes pass authenticated public checks. Public login returns
200; unauthenticated app and API return 307 and 401. Six desktop/mobile browser
journeys pass. All five services are active with zero automatic restarts. Existing
history counts and encrypted Google/source credentials are preserved; configuration
hashes are unchanged, excluding generated Registry metadata. The original failed
run is byte-for-byte preserved and its HTTPS view explains the incorrect query.
See [verification](verification.md) for test evidence and controlled-model limits.

Application-only backend rollback, if needed:

```
.venv-integrations/bin/python .local/overview-knowledge-fix-20261110/release_control.py rollback
```

This restores only the three pre-hotfix source files and restarts backend services
and the worker. It does not restore databases, provider journals or the frontend.
