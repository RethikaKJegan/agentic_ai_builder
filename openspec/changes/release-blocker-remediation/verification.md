# Release blocker remediation — 7 November 2026

**Website preview published. Production readiness remains NOT READY.**

The user's latest instruction explicitly authorized website deployment and
prioritized desktop prompt testing. The tested frontend is published at
https://praxi.bellcorpstudio.com/login using the existing password-gated preview.
Only `agentic-builder-frontend.service` was restarted. Backend PID 1203436 and
worker PID 1203437 were unchanged. No database migration/restore, credential or
reverse-proxy change, paid model call or real external effect was performed.
Backend source fixes described below are implemented and under isolated
qualification; this frontend-only publication does not load them into live
backend processes. No live prompt/model success is claimed by the HTTP checks.

## Completed evidence

| Check | Passed | Failed | Skipped | Scope |
| --- | ---: | ---: | ---: | --- |
| Complete browser round r2 | 151 | 0 | 0 | All 48 spec files; desktop/mobile/single-project cases retained |
| Frontend unit suite | 539 | 0 | 0 | 82 files; final frontend source |
| Worker drain regressions repeated | 30 executions | 0 | 0 | Three distinct cases, each repeated in ten fresh processes |
| Earlier complete backend comparison | 2,533 | 0 | 0 | Four partitions; before final two extension regressions/routes; excludes separate outage |
| Final current-source backend collection | 2,536 collected | — | — | Complete execution restarted and still pending; not a pass claim |

Final frontend types, lint and isolated production build pass. API contracts,
generated UI schema drift, SQL inventory drift (1,192 calls, 123 literal tables),
whitespace and strict scoped OpenSpec checks pass. The current complete backend
rerun includes PostgreSQL, Simpson/Subway and the added regressions; results must
be read from its completed evidence, not inferred from earlier runs.

Public HTTPS smoke checks: `/login` returns **200**, unauthenticated `/app` returns
**307**, and unauthenticated `/api/backend/workflows` returns **401**. The existing
login configuration and backend routing remain enforced. The deployed build ID,
previous build ID, rollback location and exact publication scope are recorded in
`evidence/preview-deployment.json`. The prior frontend build is retained under
ignored `.local/release-blocker-remediation/frontend-rollback-build`.

## Confirmed fixes and retained acceptance intent

- All 49 originally unsuccessful browser scenarios now have passing observations
  in the complete r2 round. `evidence/browser-remediation-map.json` records their
  retained intent. No scenario was deleted, skipped or replaced with a weaker
  success assertion. Existing Questions remains available with its permissions.
- Existing revision operations are reachable under **Manage saved revisions**;
  existing structural relationship and source-mapping reviews are reachable under
  **Review source links and mappings** within Semantic Intelligence. These reuse
  existing components and permission/version/staleness checks.
- Restored the existing accessible graph outline/connection editor. Distinct
  branch outcomes to the same destination are preserved; undo/redo captures its
  snapshot before deferred React updates. Desktop/mobile historical-design and
  persisted release journeys exercise the actual canonical documents and runs.
- The frontend proxy forwards only the exact additional extension-session cookie;
  unrelated-cookie filtering, trusted tenant routing and origin checks remain.
  Standalone extension submission and release-state routes delegate to existing
  shared services with exact references, idempotency and permission checks. Two
  regressions cover duplicate submission, mismatch, revoked permissions, scoped
  release visibility and zero provider effects.
- API factory imports no longer construct a default application/database. Explicit
  ASGI app lookup retains supported construction. Fresh-process audit tests reject
  SQLite connections during factory import; earlier private startup guards remain.
- Worker leases start after transaction-lock acquisition, expired owners cannot
  renew, polling respects short TTLs and heartbeat covers the entire parallel and
  singleton drain. Two new regressions fail against the old supervisor. The
  original short-TTL drain scenario now uses controlled clock/heartbeat barriers;
  execution budgets, ownership checks and lease duration are not increased.
- Adaptive state refresh remains a scoped read during pending commands. Regression
  verifies no duplicate mutation; browser orchestration awaits the actual drive
  response rather than treating a normal bounded server call as an immediate
  disabled-button failure. Runtime deadlines and execution budgets are unchanged.
- Legacy browser navigation follows current labels, details/disclosures, automatic
  planning and canonical automation selection. Archived investigation-plan tests
  retain saved plan/evidence/run/report/reload checks; current prompt orchestration
  remains covered by the actual backend scenarios. Extension cases use exact
  Registry identities and distinct per-viewport workflow identities.

## Read-only bootstrap incident investigation

`evidence/bootstrap-investigation.json` contains independent metadata, journal
aggregates and schema comparisons. The 3 November backup has 106 schema objects;
current main-file inspection has 124. SQLite inspection used `mode=ro&immutable=1`
and query-only mode, read no business rows and performed no restore or write.
Immutable inspection excludes active WAL and is not a consistent live snapshot.
Days of legitimate intervening changes prevent attributing differences to the
bootstrap incident. Available service logs have database errors but no attributable
bootstrap transaction audit or immediate pre-run fingerprint.

**Historical shared-store impact remains BLOCKED for independent operator audit.**
The preventive import defect is fixed; earlier record/schema equivalence cannot
be established from this evidence. No blind restore or shared-data repair occurred.

## Reproduction, interrupted checks and pending final qualification

All backend commands use the existing `.venv-integrations` Python with
`PYTHONDONTWRITEBYTECODE=1`, `-B -m pytest -q -p no:cacheprovider`, controlled
providers and tracing disabled. Private restricted-role DSNs are not printed.
Four independent disposable PostgreSQL databases avoid auxiliary-schema collisions.
The owned PostgreSQL 16 cluster uses its private Unix socket, port 55437, no TCP.

Final collection is `/tmp/remediation-release-collected.log` (2,536 cases).
Current full execution uses `.local/release-blocker-remediation/run_qualified_shard.py`
for partitions 0–3. Logs are `/tmp/remediation-release-resumed-backend-N.log`;
JUnit is `.local/release-blocker-remediation/release-final-backend-N.xml`.
After all four complete, the isolated coordinator runs only
`tests/test_production_outage.py`, writes `/tmp/remediation-release-outage.log`
and `outage.xml`, records `evidence/backend-results.json` and stops only the owned
test cluster. It does not restart production services. Fake lease advancement in
that outage check is not a measured production recovery SLO.

Browser commands use the isolated `frontend-v4` build and matching original
Playwright configurations, one worker per group, distinct private fixture stores
and loopback ports. Groups are general0–general3, phases, login, lifecycle,
orchestration and extension. `evidence/browser-results.json` contains actual r2/r3
case observations. Each complete round contains exactly 151 logical scenarios;
repeated runs do not increase distinct coverage.

The initial r2 lifecycle startup refused an occupied loopback port before executing
any scenario. Its diagnostic log was retained; only verified orphan test processes
were stopped and all 14 actual cases then passed. The environment/access transition
around 09:04 UTC ended full-backend coordinators and part of r3 before completion.
Those interrupted runs are not clean qualification. The current full backend run
and remaining second-round browser groups were restarted as detached isolated jobs.
Earlier targeted/interrupted attempts are diagnostic history, not added passes.
A concurrent frontend-unit attempt timed out in an unchanged graph unit; the final
bounded two-worker suite passes all 539 cases without changing its timeout.

## Remaining release gates

| Gate | Status |
| --- | --- |
| All original 49 browser failures remediated; complete round | PASS: 151/151 |
| Second complete reproducible browser round | PENDING: remaining isolated groups running |
| Final complete 2,536-case backend and separate outage | PENDING: running; no final pass count claimed |
| Frontend units/types/lint/build and contract/source gates | PASS within stated scope |
| Shared-default historical incident impact | BLOCKED: independent pre-incident audit/backup evidence absent |
| Production individual authentication | BLOCKED: existing backend deliberately rejects production mode |
| Verified staging multi-host/network/storage failure qualification | BLOCKED: topology/targets not supplied |
| Live providers/model judgment/delivery | BLOCKED: no explicit sandbox targets/budget; no live calls made |
| External alert delivery/acknowledgement and metrics aggregation | BLOCKED: representative deployed monitoring not qualified |
| Coordinated production backup RPO/RTO and rollout/rollback rehearsal | BLOCKED: representative infrastructure/objectives absent |
| Soak/SLO/fairness and scaling beyond one host | BLOCKED: no representative workload/SLO; advisory write lock retained |
| Global credential quotas across separate authoritative stores | OPEN architectural limitation; local counters do not coordinate separate deployments |

Desktop prompt testing is available on the existing preview. That publication is
not a production-readiness declaration. Prior Phase 1–3/final-validation evidence
and unrelated contributor changes remain preserved; no git staging/commit occurred.
