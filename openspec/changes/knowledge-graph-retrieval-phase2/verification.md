# Verification — 18 October 2026

## Backend

- 75 passed: retrieval, source selection, detailed graph, relationships and source
  discovery (`backend-retrieval.log`).
- 85 passed, 3 additional skips: native database workflows, bounded queries,
  query jobs, business graph reviews and automatic refresh
  (`backend-workflows.log`). Skips are not counted as passes.
- Final backend changes: 31 passed in retrieval + native workflow regressions
  (`backend-final.log`); final extra execution-scope assertion: 10 overlapping
  retrieval tests passed (`backend-retrieval-final.log`).
- Tests cover 154 saved datasets, one-source model context, owned isolation,
  disconnect/review invalidation, stale generation revisions, ambiguity, source
  injection rejection, three-hop path expansion, unavailable/suggested links,
  agent context bounds, HTTP session/origin protection and the additive contract.
- A private copy of actual Northwind metadata selected products, categories,
  and products/categories/suppliers correctly; the combined case had two usable
  relationships (`real-metadata-check.json`). It did not contact source databases.

## Frontend and browser

- 59 passed: data-source UI plus new source preview and database workflow review.
- 33 passed in a second focused run: preview/subgraph, workflow review and API
  proxy; seven overlap the previous run (85 distinct UI tests across the runs).
- Types, scoped lint, shared contract validation and generated contract drift
  check passed. Strict OpenSpec validation passed.
- Isolated production build QCWDXZvX-tP8HfUkJBzCP passed with source parity.
- Existing production desktop/mobile browser scenarios: 36 passed. Both new
  preview scenarios initially hit an ambiguous test text locator; changing it to
  the status role yielded 2 passed. No product change was needed for that fix.
  Together these verify 38 desktop/mobile scenarios against the final build.

## Release

The initial no-active-run guard stopped rollout while short scheduled procurement
runs continued. The verified WorkerSupervisor graceful drain was then used to
stop new scheduling and finish in-flight work. A private SQLite backup was taken;
no workflow, event or approval was cancelled or edited. Queued work remains
persistent. All three services resumed, and the metadata preview returned 12
indexed datasets and the expected single products source.

356 previous static assets were retained. Configuration and database write-policy
hashes are unchanged. Live acceptance permits only GET and the metadata preview
POST; workflow/model generation and external-action requests are blocked by the
browser guard. Final public/local desktop/mobile proof is recorded in
`.local/kg-phase2/activation/browser.json`: four local/public desktop/mobile checks passed; each verified all three Northwind prompts, with zero page errors, missing assets or unexpected mutation requests. Screenshots were also captured.

No claim is made of a new live model-generated email/calendar workflow, arbitrary
cloud-connection scale, semantic embeddings, new write grants or Praxi changes.
Legacy `/data-ontology` endpoints and storage names remain for compatibility;
product labels use Knowledge graph.
