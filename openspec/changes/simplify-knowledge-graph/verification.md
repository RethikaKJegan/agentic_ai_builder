# Essential KG controls verification — 18 October 2026

Only the Knowledge graph tab presentation and affected tests/docs changed. Removed
record exploration, entity modes, semantic generation button and all editing/review
panels. Preserved regeneration, per-connection automatic refresh settings,
search/status/connection filters and essential zoom/pan/fit. Fixed physical dataset
scope when displaying one connection; combined view retains cross-database links.
No backend/planner, credentials, inference flags or write policies changed.

Evidence under `.local/kg-essential/`:
- `tests.log`: 11 tests passed across 4 relevant files, including connection-boundary
  filtering, reduced controls, regeneration, automatic refresh and source preview.
- `types.log`, `lint.log`: TypeScript and lint passed.
- `build.log`: isolated production build passed.
- `browser.log`: 8 desktop/mobile tests passed; regenerate/settings use intercepted
  APIs, no cloud/model actions. Includes existing PostgreSQL/MongoDB/combined
  source-preview browser regressions.
- `activation-verified/result.json`: live build iqRTeb3DiyEQ8QX3iG2it; 407 static
  assets retained, unchanged backend/worker PIDs and configuration hashes.
- `live-browser.log`: read-only live desktop/mobile checks; all three connection
  options render, removed panels absent, no page errors or horizontal overflow.

An initial activation health check used the raw authenticated backend endpoint
without a session and received 401; automatic rollback restored the previous
frontend. The final activation uses the normal frontend session and passed.
Underlying backend KG context remains independent of the browser's display filter.
Regeneration rebuilds discovered metadata; unchanged semantic proposals are reused.
