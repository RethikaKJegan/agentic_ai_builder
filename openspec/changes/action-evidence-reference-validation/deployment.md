Latest hosted runtime update: [query clarification guidance](../query-clarification-caveats/deployment.md).

# Hosted evidence-reference fix — 10 November 2026

Deployed to **https://praxi.bellcorpstudio.com/**.

- Release: `evidence-reference-20261110-e660db89aee0`.
- Source manifest SHA-256: `e660db89aee02bdef7f08768d4a36575f4e900a146a22d1fdb76e324a0fe043a`.
- Base commit: `36fc5cee6c7abf19107a1563064c72ffceedfad0` plus the existing recorded changes and this two-file backend fix.
- Frontend artifact retained: `73n0K7eciFUQ8gCNaRgsi`.
- Completed: 2026-11-10T12:54:29.840557+05:30 (India time).

## Change and qualification
Known action evidence references now become explicit dependencies during automatic-input planning. Unknown references are validated inside the existing bounded correction boundary with precise diagnostics; they are never promoted into evidence or silently removed. Repeated invalid proposals, explicit invalid plans, cycles and conditional dependencies remain blocked. Existing query bindings, selected-account ownership and exact-payload approvals remain enforced. No shared contracts or database schemas changed.

The scoped suite passed 164 tests, plus a separate real-runtime query/report/approval test using fixture HTTP providers. A controlled replay of the user's exact natural-language prompt passed against copied Simpson state, preserving the selected account and approvals. The original production proposal was not retained, so no claim is made about its exact invalid reference. No live model interpretation or live population query was qualified by this rollout.

## Preservation and rollout
Fresh verified online SQLite snapshots of main/Simpson/Subway stores passed quick_check. Backups also preserve 53 credential/configuration files, nine provider-state files, source and frontend artifact. Baseline/candidate startup, authentication and API rehearsals passed across all three copied stores with networking/workers disabled and protected-record guards enabled. The existing systemd backend/worker rollout checked for active work and schedules before activation and retained application-only rollback. No destructive migration, data restore or credential change occurred.

Post-deployment authenticated public session, Business Investigation, Data Intelligence Questions configuration, Registry and worker-health checks passed for all three routes. Six desktop/mobile browser journeys passed with API mutations blocked, zero page errors and preserved historical clarification. All five services are active with zero automatic restarts. No critical backend/worker log entries were found during monitoring. Existing history counts, encrypted credentials and configuration hashes passed preservation checks.

No paid model call, live workflow submission, real email, Sheets write or other external tool effect was performed. The historical shared-store audit and unapproved business-definition limitations remain separate and unresolved.

## Application-only rollback

```sh
.venv-integrations/bin/python .local/evidence-reference-deploy-20261110/rollback.py
```

This restores only the two previous backend source files and restarts existing backend/worker services. It does not restore databases, provider journals or frontend artifacts. The previous source was rehearsed against copied stores. No rollback was required.

Private backups, manifests, test/startup/browser logs, replay.json, preservation.json and deployment.json are under `.local/evidence-reference-deploy-20261110/`.
