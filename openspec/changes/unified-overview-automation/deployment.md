> Latest frontend: [Overview-to-Workflows navigation](../overview-workflow-navigation/deployment.md),
> deployed as `workflow-navigation-20261110-68bceec971d2`.
>
> Latest backend hotfix: [immediate-work default](../immediate-workflow-default/deployment.md) is
> deployed as `immediate-default-20261110-6e8a3a832db1`, following
> [composed-intent routing](../composed-intent-routing/deployment.md),
> [short-prompt defaults](../short-prompt-defaults/deployment.md) and the
> [knowledge routing fix](../overview-knowledge-routing/deployment.md). The release below remains
> the frontend and automation baseline.

# Hosted unified Overview automation — 10 November 2026

Deployed to **https://praxi.bellcorpstudio.com/app** following explicit deployment authorization.

- Release: `overview-automation-20261110-191d33906774`.
- Base revision: `ad9398b63e6a2d609e721a50c85ffcf0c891c45d` plus the recorded source changes.
- Source manifest SHA-256: `191d3390677488c065981344e4c5f9ce764be5b6683acc0980595322f15c20a8`.
- Frontend build: `EiDLCCE7beRH3coeDHj3o`; previous build `73n0K7eciFUQ8gCNaRgsi`.
- Activated: 10 November 2026, 16:31:44 India time (11:01:44 UTC).
- Routing enabled for `local-workspace`, `client-simpsons` and `client-subway`.
- Default workspace timezone: `Asia/Kolkata`.

The existing Overview prompt now uses backend-owned structured intent routing and
existing durable planning jobs. Schedule review, authorization, recurring relative
dates, cancellation/retry and existing report-update bindings are connected to the
existing planner, Registry, CrewAI and durable runtime. Daily, weekday, weekly,
first/named-day monthly and one-time schedules use the existing scheduler.

## Qualification and rollout

Final backend routing/automation checks: 62 passed. Final binding/evidence/receipt
regressions: 73 passed. Prior qualification includes 556 frontend tests, ten
controlled desktop/mobile browser journeys, 46 disposable PostgreSQL/Mongo checks,
and the retrieval, planner, investigation and legacy automation suites recorded
in [verification](verification.md). Canonical contracts, generated contract drift,
strict OpenSpec and patch formatting passed.

Six baseline/candidate startup rehearsals passed across operator, Simpson and
Subway using copied stores, no network, no workers and guards protecting existing
history, credential, source and job rows. Candidate rehearsals verified enabled
routing. The historical Simpson workflow deleted at 08:47 UTC remained deleted;
its tombstone was preserved rather than reviving an obsolete smoke fixture.

Fresh consistent online database snapshots passed `quick_check` for all three
stores. Private backups preserve 53 configuration/credential files, provider
state, the previous frontend and rollback source. Verified source and frontend
manifests pin the exact release. An incomplete snapshot and duplicate completed
rehearsal copies were removed during preparation; verified backups were retained.
Post-rollout disk headroom was about 7 GB.

Activation used the existing service stop/swap/start mechanism and retained prior
static chunks for existing browser sessions. Only the three reviewed routing
configuration keys were added to the three isolated workspace environments.
No login credential, nginx configuration or service unit was changed. No database
restore or destructive migration was performed.

## Hosted verification

- Public `/login`: 200; unauthenticated `/app`: 307; unauthenticated API: 401.
- Authenticated public session, investigation UI, Data Intelligence, Questions,
  Registry query-tool and worker-health checks passed for all three accounts.
- Each account advertises `overview_routing_available=true` with its correct scope.
- Six live desktop/mobile journeys passed with zero page errors or overflow and
  all API mutations blocked.
- All five services are active with zero automatic restarts. No error-priority
  service journal entries were found during the rollout window.
- Existing history counts and encrypted credentials passed preservation checks.
  Configuration hashes matched except for the explicitly reviewed routing flags;
  all other configuration content was preserved.
- Verification made no paid model call, live workflow submission, real email or
  spreadsheet write. Live-model prompt acceptance is for the user's subsequent
  testing and is not implied by controlled fixture evidence.

## Application rollback

```sh
.venv-integrations/bin/python .local/unified-overview-automation-20261110/rollback.py
```

Rollback checks source identity and in-flight work, restores the prior application
source, prior routing flags and retained frontend artifact, and restarts existing
services. It does not restore databases or provider journals or delete histories.
New active schedules require explicit disposition before reverting their runtime.
The prior frontend is retained at `frontend/.next-before-overview-20261110`.
No rollback was needed. Private evidence is under
`.local/unified-overview-automation-20261110/`.

Requests still depend on authorized sources, reviewed field/date mappings,
connected accounts, concrete destinations and supported tools. Missing details
require clarification; unavailable complaint-created event subscriptions remain a
capability limitation. This release does not certify every pasted example against
live customer data or resolve historical shared-store/production-readiness gaps.
