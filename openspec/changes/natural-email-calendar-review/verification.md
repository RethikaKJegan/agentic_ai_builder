# Natural email and Calendar review — verification, 12 November 2026

Both tenant implementations reuse Overview, capability Registry, existing approvals, GraphRunner, scheduler and Google connectors. New behavior is enabled for the dedicated Simpson and Subway runtime configurations; legacy explicit/saved plans retain their prior contracts. No business records, ontology or credentials are migrated.

## Behavior and boundaries

Owned account resolution honors an explicitly selected account, then its saved default, then a sole connected account. Multiple suitable accounts receive a plain-language choice; a revoked default never silently falls back. Calendar identity defaults visibly to the connected primary calendar, or a sole operator-allowed calendar. Named/multiple calendar choices use bounded existing Calendar-list metadata only when the account already has discovery consent; no scope escalation or invented destination occurs. Missing list access offers the primary choice and Integrations setup for another calendar.

Ambiguous “prepare an email report” receives send/draft choices; explicit delivery wording is retained. The existing Overview form preserves the original objective, accumulates answers and creates a distinct request key for the amended proposal. The review displays connected account, actual recipient, selected calendar, duration and timing. Required deliveries cannot be silently dropped by generation. Normal workflow approval plus explicit recurring consent still precede execution.

After-ready reviews pin a five-minute lead, duration, timezone and completed-report dependencies. Per-run times resolve once before exact-payload approval, persist across retries and are checked against recurring consent at execution. Fixed reviews use the reviewed local time/date. A past start is rejected before Calendar invocation. A delayed report never uses the earlier workflow-trigger time as an after-ready event start.

The UI shows separate Report emailed / Review scheduled statuses only for confirmed provider receipts with identifiers. An expired, provably undispatched Calendar operation can prepare a separately reviewed Calendar-only workflow from the saved report. The original email receipt and MIME bytes remain unchanged. A possibly dispatched/unknown Calendar operation is rejected for reconciliation; it is never silently resent. Uncertain provider writes and other terminal failures remain attention states rather than automatic replays. No claim is made that all provider failures can be automatically repaired.

## Evidence

- New controlled recurring application journey: normal Overview questions → supplied answers → compiled Registry workflow → normal validation/approval → recurring authorization → two due occurrences, actual query engine, CrewAI, report, Gmail and Calendar adapters with controlled model/HTTP transports.
- Delayed approval journey: email succeeds; review time expires without Calendar invocation; separate Calendar-only preparation/approval/execution succeeds; original mail receipt and MIME bytes unchanged; uncertain dispatch marker rejects recovery.
- Scoped account selection tests cover ambiguity, foreign-owner rejection, saved defaults and revoked defaults. Fixed and after-ready timing, duration, timezone, stable recovery and tampering checks are included.
- Frontend: **23 tests passed**, including structured choice submission without automatic activation and provider-confirmed independent delivery status.
- Production frontend build, TypeScript and changed-file lint passed. Browser: **20 passed**, including desktop/mobile natural choices for both tenants and existing queued generation, cancellation, review, approval and schedule journeys. Browser provider endpoints use controlled fixtures; no real delivery occurs.
- Canonical contracts, generated UI contract comparison and strict scoped OpenSpec passed. Original schema/consent checks were not relaxed.

Initial exploratory runs exposed fixture-only recipient restrictions, simulated-clock advancement beyond a pending query timeout, terminal occurrence state naming and email object identity comparisons. The fixtures now use explicit permitted test recipients, advance clocks after the appropriate state, accept existing terminal state semantics, and compare actual MIME bytes. The legacy source-free-routing unit explicitly disables the new communication feature so it continues isolating routing without an owned Google account. The feature-enabled missing/ambiguous account behavior is tested separately. These initial attempts are not passing evidence.

Each isolated tenant candidate passed **53 backend acceptance tests**, covering natural communication, existing Calendar routing, Overview integration, reviewed recurring research, tenant isolation and Gmail. The final refined communication module then passed the complete **six-test natural communication suite on each exact candidate**. A separate affected evaluator/usage/ontology/Subway runtime suite passed **60 tests** on the checkout. The final feature-independent routing check plus natural suite passed **16 tests**. Counts overlap.

The source-free-routing test initially expected source preparation without an owned Google account; its isolated feature-off setup was corrected explicitly. The deployed feature-on behavior still asks naturally for an owned account and never invents one. Calendar-list discovery requires already-granted list scope and no real discovery was submitted during acceptance. All counts overlap and must not be added together. No live provider business-quality report, real email or Calendar event is inferred from controlled tests.

Private evidence: `.local/natural-communication-20261112/`.


## Deployment and preservation

The Simpson candidate was patched from Simpson's own previous immutable source; Subway was copied from its own active release. Only task-specific source hunks and tests were applied to Simpson. Unrelated prior Subway presentation/data fixes were not transplanted. Final immutable manifest checks passed.

Active releases:

- Simpson backend: `.local/natural-communication-release-20261112/simpsons/app`.
- Subway backend: `.local/natural-communication-release-20261112/subway/app`.
- Frontend: `.local/natural-communication-release-20261112/frontend`, build `jLAeCQVxFpkITUgWOnEEN`.

Both dedicated backend services and the frontend restarted. Shared backend and worker services retained their original PIDs and source. Consistent compressed backups exist for each tenant. All existing protected business rows, workflow/run/planning history, ontology, receipts, schedules, credentials and configuration hashes match the original backup. Existing source audit rows are preserved as an exact prefix; ordinary background profiling may append audit records. Worker heartbeat/lease health and routine source profiling-job/refresh tables are operational and excluded from equality checks; they remain backed up. No table or operational history was deleted. The first deployment check correctly stopped on these routine background updates before any service changed; the final comparison explicitly accounts for them.

Authenticated public session, tools, worker-health and query endpoints returned 200 for both tenants. Hosted Overview desktop/mobile pages loaded with zero page errors and GET-only backend traffic. Browser acceptance of actual choices/recurring review used controlled backend fixtures, while application runtime tests used real Registry/CrewAI/scheduler with controlled provider/HTTP transports. No arbitrary live-model business report, actual email, Calendar event, source write or live schedule activation was submitted or inferred. Old failed requests and prior workflows/schedules remain pinned; submit a new request for the new communication review.
