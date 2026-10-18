# Whole-app test pack

The source-control inventory below predates the detailed graph enhancement.
For the new hierarchy, business mappings and relationship qualifiers, also use
[remaining-scope Phase 1 acceptance steps](../knowledge-graph-completion-phase1.md).

Start with [the sequential manual guide](whole-app-manual.md). It contains 216
acceptance cases, test fixtures/prompts, expected results, isolation rules,
automated commands and stability qualification requirements.

Open [whole-app-results.csv](whole-app-results.csv) in a spreadsheet. Keep a
separate copy for each build/environment/device pass. Set status to PASS, FAIL,
BLOCKED or NOT RUN and fill actual result/evidence. Multi-control cases require
each named control; duplicate rows with suffixes when individual outcomes differ.

[source-controls.csv](source-controls.csv) inventories 395 source controls across
62 files in app routes, screens, features, components and navigation adapters.
Use it to check for missed buttons, fields and nested menus. Loop expressions and
shared primitives are recorded once: expand actual visible options, and mark
unused primitives explicitly rather than claiming they passed a product test.
[source-controls.json](source-controls.json) preserves the structured inventory.
These snapshots must be refreshed when source controls change; they do not prove
automated coverage.

All acceptance/control rows are NOT RUN. Preparing this pack did not execute the
whole app suite, provider writes, load tests or a stability soak. Historical
passing results elsewhere are not fresh qualification for this pack.

Known source finding: `LiveRuntimePanel` in
`frontend/src/screens/app.monitoring.tsx` uses a 5000 ms completion-to-next-read
delay while displaying “every 15 seconds.” Verify under OPS-02 and record the
discrepancy; no polling implementation was changed by this documentation task.

Use the current source and feature-specific documents when older phase documents
conflict. For example, Overview currently requests automatic input mode; the guide
does not invent a manual-input chooser. Query job restoration does not imply an
equivalent planning-job recovery UI.
