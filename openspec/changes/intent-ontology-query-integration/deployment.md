> Latest release: [query clarification handling](../workflow-query-clarification/deployment.md) is deployed as `query-clarification-20261110-fc82d6cf5e08`. Earlier release details below are historical.

> Latest backend update: [scalar recipient binding hotfix](scalar-binding-hotfix.md) is deployed as `scalar-binding-20261110-9a9ac6fa551f`. Frontend build is unchanged.

# Hosted release — 10 November 2026

Deployed to **https://praxi.bellcorpstudio.com/**.

- Release: `intent-query-20261110-e5c24bcac05d`.
- Frontend build: `C038xXGULZ07Dhwu_uq7R`; previous `R8TbH84dyZ9o_1FPkIAkL`.
- Base commit: `36fc5cee6c7abf19107a1563064c72ffceedfad0` plus the frozen 18-file source manifest, SHA-256 `e5c24bcac05d447663bfd920561c19b668e8e932a93bfa29d44e8a7bde1c3ce0`. No new commit is claimed.
- Completed: 2026-11-10T11:17:47.173087+05:30 (India); 2026-11-10T05:47:47.173087+00:00 UTC.

The new backend/frontend artifacts are active through the existing systemd service rollout. No nginx, login configuration, service units, credentials or database schema were changed. The source correction is backend-only; the unchanged frontend source was rebuilt and qualified.

Fresh verified online SQLite backups of all three stores, 53 credential/configuration files, source and prior frontend are private under `.local/intent-query-deploy-20261110/backups/`. All three database copies passed quick_check, all saved frontend files were hashed, and nine auxiliary provider files/journals were backed up with SQLite integrity checks where applicable. Six isolated baseline/candidate startup rehearsals passed with network/workers disabled and protected history/credential/job guards. A final pre-activation check found no in-flight runs/jobs or active automation schedules.

Post-release authenticated HTTPS checks passed for operator, Simpson and Subway: correct account routing, Business Investigation, Data Intelligence/Questions, generic query registration and worker health. Six public desktop/mobile browser journeys passed with zero page errors while blocking all API mutations. All five services are active with zero automatic restarts; error-priority journals since activation have no entries. History/job counts, existing encrypted Google/source credentials and credential/configuration file hashes were preserved. No database or provider journal was restored.

The prior whole-catalogue 120 KB failure is resolved for the tested complaint/purchase-order objectives on current copied stores. Simpson's literal original prompt reduces 226032 bytes to 79415 and retains tickets. Queries remain scoped to reviewed candidate datasets with current permissions/revisions. Controlled exact-prompt execution and independent fixture statistics pass; a real paid model/source execution is **pending authorization**, not claimed as passed. Questions is preserved. Historical integrity/audit gaps and missing/ambiguous business-measure definitions remain unresolved as detailed in [verification.md](verification.md).

Application-only rollback is prepared and syntax checked, with the baseline source/startup rehearsed against copied stores:

```
.venv-integrations/bin/python .local/intent-query-deploy-20261110/rollback.py
```

It restores the six prior backend files and retained frontend application artifact (`frontend/.next-before-intent-20261110`), restarts existing services, and does not restore databases or journals. No rollback was required.

Private evidence: backup-manifest.json, provider-backup-manifest.json, release-source-hashes.json, rehearsal.log, query-combined-final.log, planning-regression.log, engine-regression.log, postgres-tests.log, knowledge-regression.log, frontend-tests.log, types.log, lint-clean.log, build.log, browser.log, activation.log, https-smoke.json, preservation.json, live-browser.json and deployment.json.
