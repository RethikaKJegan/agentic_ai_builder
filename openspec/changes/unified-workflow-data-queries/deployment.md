> Latest release: [empty-query report tables](../empty-query-report-tables/deployment.md) is deployed as `empty-report-20261111-cb5425fdfdac`. Earlier details below are historical.

> Latest release: [verified aggregate percentages](../verified-aggregate-percentages/deployment.md) is deployed as `aggregate-percent-20261111-19ec7bd63922`. Earlier details below are historical.

> Latest release: [scoped query model output](../scoped-query-output/deployment.md) is deployed as `scoped-query-20261110-ce2917824f4b`. Earlier details below are historical.

> Latest release: [generic email planning correction](../email-draft-planning/deployment.md) is deployed as `mail-planning-20261110-a13b9929c6de`. Earlier details below are historical.

> Latest release: [query validation and worker lease correction](../query-projection-worker-release/deployment.md) is deployed as `query-worker-20261110-957b64db5e4f`. Earlier release details below are historical.

> Latest release: [execution-approval routing correction](../execution-approval-routing/deployment.md) is deployed as `execution-approval-20261110-c86221afff7e`. Earlier release details below are historical.

> Latest release: [question-free workflows](../question-free-workflows/deployment.md) is deployed as `question-free-20261110-69a3569eb75f`. The release details below are historical.

> Latest backend: [immediate-work default](../immediate-workflow-default/deployment.md) is deployed as `immediate-default-20261110-6e8a3a832db1`. Frontend retains [Overview-to-Workflows navigation](../overview-workflow-navigation/deployment.md). Earlier release details below are historical.

Latest hosted query release: [mixed-numeric HMR fix](../mongodb-mixed-numeric-queries/deployment.md).

Latest hosted frontend release: [tenant-isolated workflow Knowledge Map](../workflow-knowledge-map/deployment.md).

Latest hosted backend update: [evidence continuation and Calendar timing](../workflow-evidence-continuation/deployment.md).

Latest hosted public research fix: [tenant web-search availability](../public-research-availability/deployment.md).

Latest hosted runtime release: [grouped query fix](../grouped-query-model-output/deployment.md).

Latest hosted runtime update: [query clarification guidance](../query-clarification-caveats/deployment.md).

Latest hosted backend release: [evidence-reference validation fix](../action-evidence-reference-validation/deployment.md).

> Earlier release: [query clarification handling](../workflow-query-clarification/deployment.md) is deployed as `query-clarification-20261110-fc82d6cf5e08`. Earlier release details below are historical.

> Updated release: the 10 November intent/ontology discovery and binding correction is now deployed. See [current deployment](../intent-ontology-query-integration/deployment.md). The catalogue limitation below records the 9 November release state.

# Hosted deployment — 9 November 2026

Deployed to **https://praxi.bellcorpstudio.com/**.

- Release: `unified-query-20261109-e0846ca024af`.
- Frontend build: `R8TbH84dyZ9o_1FPkIAkL`; prior build `KQHhQpTBedkYc5z5IxDWh`.
- Base commit: `36fc5cee6c7abf19107a1563064c72ffceedfad0` plus the recorded unified-query source changes.
- Source manifest SHA-256: `e0846ca024af8af059d5b8dc24b1709235178fd9f3b373e6879f625855c4fa1c`.
- Completed: 2026-11-09T17:17:15.199942+00:00 (UTC).

This supersedes the earlier stopped preflight after the user explicitly directed
proceeding with the hosted application deployment. The historical shared-store
incident was not retrospectively resolved or repaired by this rollout.

## Preparation and preservation

Verified private release backups are retained under
`.local/unified-query-deploy-20261109/backups/`: consistent online SQLite snapshots
of the main/Simpson/Subway stores, each passing quick_check; 51 configuration and
credential files; source archive; and the previous frontend artifact. All 398 saved
frontend files were checked against the then-active artifact. Nine provider
journal/resource/configuration files were additionally backed up with integrity
checks for SQLite stores. No credential values are included in this public report.

Both rollback baseline and candidate source passed copied-store startup/auth/API
checks for all three accounts. No network access or workers were allowed during
rehearsal. SQLite write guards prohibited updates/deletes/drops to existing history,
credential, source and job tables; protected counts and credential/job checks passed.
No release-specific destructive migration was run. No database was restored.

The main shared worker was stopped, backend/tenant services restarted through
existing systemd units, the worker restarted, and the frontend switched to the
verified artifact through the existing stop/swap/start process. Previous static
chunks were retained for existing browser sessions. No nginx, login credential or
service-unit configuration was changed.

Post-deployment checks show history/job counts preserved across all three stores,
existing encrypted Google/source credentials unchanged, and credential/configuration
file hashes unchanged (generated Registry metadata excluded). No pending runtime
work or active automation schedules existed at the pre-deployment snapshot.

## Verification

- Essential backend/contract/startup-isolation suite: 36 passed, one PostgreSQL
  case skipped without a DSN; prior isolated PostgreSQL evidence remains separate.
- Latest frontend production build: passed using the site's existing configuration.
- Exact artifact desktop/mobile fixture browser checks: two passed.
- Public HTTPS /login: 200; unauthenticated /app: 307; unauthenticated API: 401.
- Authenticated public checks passed for operator, Simpson and Subway: session,
  Business Investigation, Data Intelligence, Questions configuration, registered
  generic query tool and worker health all returned 200 with correct account scope.
- Six live browser journeys passed (desktop/mobile for all three accounts): Overview,
  Business Investigation prompt/account selector and Questions tab; zero page errors
  or horizontal overflow. All API mutations were blocked during these journeys.
- All five services remain active with zero automatic restarts after activation.
- No paid model call, live workflow submission, email, Sheets write or other external
  tool action was triggered by deployment verification. Existing workflow histories
  and schedules were not edited.

## Working features and limits

The recent frontend/backend changes are loaded on the public site. Natural-language
prompt entry, account routing, selected-account controls, the new Registry query
capability, workflow/report UI and the existing Questions tab are available.

**Live no-ID query execution is not qualified and is currently constrained:** the
current metadata catalogues for operator/Simpson/Subway exceed the generic query
planner's 120 KB catalogue bound (`DATA_QUERY_LIMIT`). Rehearsal found this on actual
copied account stores. Connected planning therefore cannot expose an unrestricted
generic catalogue for these current account scopes. This is a functional limitation,
not a deployment/service-health failure. No successful live CrewAI query/report
execution is claimed. Earlier controlled integration evidence remains valid but
is not evidence of successful execution against these oversized live catalogues.

Automatic schedule creation from natural-language text, runtime query clarification/
resume and recurring relative-date semantics remain incomplete as described in
verification.md. The historical database audit and other production-readiness
qualification gaps remain separate. This release does not certify full production
readiness or resolve them.

## Application rollback

Prepared application-only rollback:

```
.venv-integrations/bin/python .local/unified-query-deploy-20261109/rollback.py
```

It stops the affected services, restores the rehearsed baseline backend source
files and previous frontend artifact, and restarts the existing services. It does
**not** restore databases or provider journals. The previous active artifact is
retained at `frontend/.next-before-unified-20261109`. No rollback was needed.

Private machine evidence: backup-manifest.json, provider-backup-manifest.json,
release-source-hashes.json, rehearsal.log, release-tests.log, browser.log,
deployment.json, https-smoke.json, preservation.json and live-browser.json in
`.local/unified-query-deploy-20261109/`.
