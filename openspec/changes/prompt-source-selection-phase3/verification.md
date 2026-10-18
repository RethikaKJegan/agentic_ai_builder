# Verification — 18 October 2026 (IST)

## Implemented

- Confirmed, current owned business mappings are included in metadata-only model
  planning; other review states and unsupported field IDs are excluded. Shared
  entity names never establish executable joins or permissions.
- Server-derived optional selection_preview includes selected dataset identity,
  qualified paths, required fields/types/purposes, deterministic plan-usage reasons,
  ordered eligible equality pairs, confirmed relevant concepts and coverage warnings.
- Questions shows an interactive highlighted graph, keyboard/dropdown selection,
  inspectable source details and logical-plan intent before any execution.
- Successful native/federated/fallback results return the optional executed_plan
  logical snapshot. Existing source reads, timing, join checks and fragments remain
  distinct execution evidence. Native query text is not fabricated or exposed.
- Jobs preserve the original source preview across coordinator restart. Legacy
  plans without preview metadata execute normally. Freshness/authority gates remain.

## Fresh verification

- 137 backend tests passed; 53 integration tests were skipped because the required
  isolated PostgreSQL test DSN was not configured. Skips are not passing database
  equivalence evidence. Command:

  `.venv-integrations/bin/python -m pytest -q tests/test_data_selection.py tests/test_data_queries.py tests/test_data_graph_v2.py tests/test_data_relationships.py tests/test_data_sources.py tests/test_data_query_jobs.py tests/test_data_query_pushdown.py tests/test_data_query_federation.py`

  New coverage includes PostgreSQL-only, Mongo-only and combined selection;
  exact field uses/pairs; no planning reads; unrelated-source exclusion; confirmed
  review filtering; owned isolation; confirmation not granting joins; clarification;
  stale-plan rejection; immutable job preview recovery; planning-review races;
  executed logical plan identity; and legacy compatibility.
- 128 frontend/domain/proxy tests passed using `npm run test --
  src/features/data-sources src/domain src/api/phase1-proxy.test.ts`.
  Tests inspect selected sources, keyboard/dropdown navigation, qualified linking
  pairs, confirmed concepts, coverage, no execution before Run, completed logical
  query evidence and preview clearing/clarification. Initial nested-text assertion
  failures were corrected before the final passing run.
- TypeScript and scoped ESLint passed. Isolated Next.js production build passed
  at `.local/phase3-selection/frontend/.next`. Logs:
  `.local/phase3-selection/{frontend-tests,types,lint,build}.log`.
- Contract schema/fixture validation, generated UI contract drift check and strict
  OpenSpec validation passed. The additive contract is authoritative; no human
  contributor acceptance is claimed.

- All 22 production desktop/mobile Chromium browser scenarios passed using
  `GRAPH_FRONTEND_DIR=/home/raf/agentic-ai-builder/.local/phase3-selection/frontend
  npm run test:e2e -- --config playwright.graph.config.ts`. Six new cases cover
  PostgreSQL-only, Mongo-only and combined previews on both viewports, explicit
  execution, completed logical-plan evidence, clarification and preview clearing.
  Existing graph, relationship, query and job scenarios also passed. New scenarios
  assert no page errors and no document-width overflow. Fixtures validate UI
  behavior, not real model choices or live database results. Log:
  `.local/phase3-selection/browser.log`.
- Whitespace checks passed for the changed implementation, test, contract and
  documentation files, including the new untracked files.

## Practical limits and deployment

No new join semantics were added. Anti/outer/many-to-many joins and unsupported
queries must clarify/fail; native SQL/MongoDB pipeline dumps are not shown.
The model still selects intent from a bounded catalog; validation does not prove
semantic relevance. User review and live acceptance remain necessary.

This is a workspace implementation with an isolated production build. No live
deployment, service restart, source-row write/read, credential edit, relationship
review change, live provider/model invocation, or Praxi modification was performed.
No broader legacy-suite, production-readiness, physical-device or live cloud/model
correctness claim is made. Existing historical live evidence is not fresh evidence
for these additions. See `docs/prompt-source-selection-phase3.md` for UI acceptance.
