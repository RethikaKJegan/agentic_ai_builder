# Hosted Subway deployment — 12 November 2026

Deployed and verified at **https://praxi.bellcorpstudio.com/**.

- Final release: `subway-procurement-20261112-89aa4661984a`.
- Activated at **5:16:29 PM India time** on 12 November 2026 (`2026-11-12T11:46:29Z`).
- Actual source: `/home/raf/agentic-ai-builder/.local/subway-procurement-release-20261112-r2/app`.
- Subway's existing database, credentials, source connections and hosted frontend are retained.
- Only `agentic-builder-subway` was restarted. Operator, Simpson, shared worker and frontend PIDs remained unchanged.

Subway previously shared its code directory with the other services. This rollout copies that exact active runtime into a separate Subway release and applies only the recorded procurement changes. The original shared release files remain byte-for-byte unchanged, including files Simpson may import lazily. Unrelated ongoing checkout work is excluded.

The Subway-only systemd override is `/etc/systemd/system/agentic-builder-subway.service.d/zzzzz-subway-procurement-release.conf`. Existing base unit and earlier release override remain unchanged. The first attempt used a lower-priority override and safely rolled back when path verification detected the old source. The final activation checks both effective systemd configuration and actual process working directory, with rollback to the previously verified Subway release available. No database restore was performed.

Final verification:

- Exact final artifact: **74 acceptance tests passed**.
- **57** explicit evaluator/usage/conditional/pagination regressions and **24** existing Knowledge Map UI tests passed; counts overlap with other runs as detailed in verification.md.
- Six real-source assessments passed on copied application state using the existing restricted read-only Subway snapshot reader.
- Authenticated public session, tools, worker health, data-query route and investigation page return 200. New assessment/query/document tools are registered.
- Public `/login` is 200, anonymous `/app` is 307 and anonymous API access is 401.
- A genuine Simpson source ID is unavailable to authenticated Subway (404).
- Subway history counts, Google/source credentials, original ontology versions, client packages and schedules are preserved. Other service PIDs and shared source hashes are unchanged. Subway remains active with zero automatic restarts at verification.
- No production workflow submission, paid model request, source write, email, Sheets write or Calendar action was triggered by smoke verification.

Source limitations remain visible: historical snapshots, unavailable requisition links/PR approvals/reservations, missing invoice currency/items/due dates and unverified cross-system store/vendor identity. Modeled scenarios are not installed as operational data. Start a new Subway workflow to use the new planning context; existing immutable reviewed workflows and schedules are not silently rewritten.

Private evidence and consistent compressed Subway backup: `.local/subway-procurement-20261112/`. `deployment.json`, `https-smoke.json`, `release-manifest.json` and the final acceptance/rehearsal logs identify the active artifact and preservation checks. Application rollback reinstates the saved `subway-r1-override.conf`, reloads systemd and restarts only Subway; the previous source is retained. Database restoration is not part of application rollback.
