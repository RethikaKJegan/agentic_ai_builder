# Phase 1 verification — 18 October 2026 (IST)

Implemented the metadata-only business ontology, reviewable predicates/direction,
source/evidence inspector, entity canvas and automatic metadata refresh. Phase 2
retrieval is not included. No Praxi files, Google credentials, write policies or
existing workflow definitions were changed. New contracts are additive; no human
contributor signoff is inferred.

## Fresh automated checks

- 77 backend tests passed across ontology, refresh scheduling, source discovery,
  relationships, detailed graph and source-selection suites. New tests verify real
  projection/contracts, qualified field evidence, predicate direction/reset,
  persistence, stale/concurrent edits, source ownership, safe HTTP envelopes,
  unchanged automatic checks, changed schema rebuilds, failure/backoff/recovery,
  schedule coalescing and disconnect during publication.
- 103 further backend regressions passed; three integration tests were skipped
  and are not counted as successful database equivalence checks. Coverage includes
  native PostgreSQL/MongoDB workflows, read queries/jobs, Google account binding,
  and procurement composition through offline provider boundaries. No cloud writes
  or real emails/calendar actions were triggered by these tests.
- 140 frontend/domain/proxy tests passed across 17 files. The initial checkbox
  selector ambiguity and strict test indexing were fixed. One existing fake-timer
  graph test timed out under concurrent compilation; the entire affected suite
  passed with file parallelism disabled. No existing test timeout was increased.
- Final TypeScript, scoped ESLint and isolated Next production build passed.
  Build artifact: .local/ontology-phase1/frontend/.next; build.log beside it.
- 36 production Chromium desktop/mobile fixture scenarios passed, including new
  ontology source/evidence selection, predicate reversal/review, refresh settings,
  reload persistence, zoom, no page errors and no horizontal overflow. Existing
  query, job, CRUD and workflow review scenarios also passed. Browser responses are
  fixtures; backend tests separately verify persistence and scheduling.
- Shared contract validation, new ontology/refresh response-schema tests and strict
  scoped OpenSpec validation passed. Existing-file diff whitespace checks passed.

## Deployment and real read-only acceptance

Activated build 7XQosrkQgXqVcqcxKZPSD from the source-matching isolated artifact.
Previous build s8AXfHzKo306b6DcfGzYL and private SQLite backup are retained in
.local/ontology-phase1/activation/. Retained 332 previous static assets. Existing
.env and database-write-policy bytes were verified unchanged. All three Builder
services are active after the controlled restart; no planning or execution was
active at rollout.

Real authenticated APIs return ontology version 1, 12 entities, 10 business
relationships and two refresh schedules. Four actual Chromium checks passed:
local/public origins at desktop/mobile sizes, entity and relationship-label clicks,
source field details, zoom/fit, refresh controls, reload, no browser errors, no
missing assets and no page-width overflow. A browser guard blocked mutations and
observed none. The first browser attempt raced rollout; the next used an SVG edge
bounding-box center that lay off the actual line/label. The final checks click the
visible label and all four pass. Screenshots were visually inspected.

Both Northwind sources subsequently completed real automatic metadata profiling.
Atlas and Supabase retained metadata revision 8 and credential generation 8; the
technical graph retained revision 41. Freshness timestamps advanced. Saved schedules
are enabled at 300 seconds. This proves automatic read-only discovery ran without
manual refresh and unchanged structures did not invalidate versions. New-source
structural changes and failed-cloud cases were tested with fixtures, not cloud
schema mutations. No database record write, email, Calendar action or live model
request was performed. Actual phone/WebKit acceptance is separate.

Evidence: .local/ontology-phase1/{browser.log,build.log}, activation/result.json,
activation/browser.json, activation/automatic-checks.json and desktop/mobile PNGs.

## Practical limits

Automatic refresh runs within configured database/schema scopes, at 60–86400 second
intervals, with default 300 seconds, bounded profiling, backoff and worker-dependent
execution. It is not instantaneous change-stream delivery. Manual refresh preserves
its existing explicit invalidation behavior. MongoDB sampling does not prove field
deletion. Business labels initially use conservative references/related-to wording;
review and rename them. Business review never grants an executable join. Canvas
shows 80 matching entities and supports search/filter for the rest. Existing shared
demo identity, graph/query bounds and lack of Phase 2 large-catalog retrieval remain.
