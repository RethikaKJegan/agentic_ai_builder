Latest hosted backend release: [evidence-reference validation fix](../action-evidence-reference-validation/deployment.md).

# Hosted query-binding hotfix — 10 November 2026

Deployed to **https://praxi.bellcorpstudio.com/**.

- Release: `query-binding-20261110-0b3f369c5bde`.
- Source manifest SHA-256: `0b3f369c5bdeee0a543a063231b974ff7807be1cc1fb9b62e4fb07153cd5ed24`.
- Base commit: `36fc5cee6c7abf19107a1563064c72ffceedfad0` plus the existing recorded application changes and this three-file backend hotfix.
- Frontend artifact retained: `73n0K7eciFUQ8gCNaRgsi`.
- Completed: 2026-11-10T07:03:33.804020+00:00.

Fresh verified online snapshots of main/Simpson/Subway stores passed SQLite quick_check. Backups also preserve 53 configuration/credential files, nine provider-state files, source and the active frontend. Baseline/candidate copied-store startup checks passed for all three accounts. The deployment used the existing systemd backend/worker process, checked for active work/schedules before activation, and retained application-only rollback. No destructive migration, database restore, credential edit or external provider action occurred.

Post-deployment authenticated HTTPS session, Business Investigation, Data Intelligence Questions configuration, Registry query tool and worker-health checks passed for all three routes. Six desktop/mobile browser journeys passed with all API mutations blocked, no page errors and the existing saved clarification visible after refresh. All five services are active with zero automatic restarts; no critical backend/worker log entries were found during the deployment window. Preservation checks found existing history counts retained, encrypted credentials unchanged and configuration file hashes unchanged.

The exact failed proposal was qualified offline against copied Simpson data. No paid model call or live workflow execution was performed. No real emails or Sheets writes were triggered. Historical shared-store audit and business semantic approval limitations remain as previously recorded.

Application-only rollback, with the baseline rehearsed against copied stores:

```sh
.venv-integrations/bin/python .local/query-binding-deploy-20261110/rollback.py
```

Rollback restores only this release's previous backend source and restarts the backend/worker services. It does not restore databases, journals or frontend artifacts. Private evidence and verified backups are under `.local/query-binding-deploy-20261110/`.
