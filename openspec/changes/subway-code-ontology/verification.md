# Subway code ontology verification — 6 November 2026

## Deployed result

`bov_subway_code_v2` is active in Subway's existing isolated workspace. It contains
89 concepts, 91 relationships, 28 descriptive implementation rules, 15 modules and
five layers. New planning selects package `subway-business-v1` revision 2. Original
ontology version/package revision 1 remain immutable and accessible.

All eight original ZIP hashes and selected member/excerpt hashes were verified.
Only reviewed excerpts were extracted privately; supplied applications were not run.
Each definition cites exact source quotations. Service namespaces remain separate;
code-only models have no invented data source or join authority. Known defective
guards and questionable authorization exceptions are recorded in
`docs/subway-code-ontology.md`. Rules remain non-executable descriptions, not
independently verified company policy. OWL/SHACL definition validation passed;
instance-level validation/reasoning and policy approval were not performed.

## Checks

- Scoped ontology, authentication, isolation, compiler and planning suite: 67 passed.
- Final scoped view/reference/rule suite, including nine new ontology tests: 45 passed.
- Existing connected-action planning and business generation regressions: 74 passed.
  These suites overlap; their counts are not a distinct-test total.
- Frontend: 529 tests passed; typecheck, lint and production build passed.
- Shared contracts and strict OpenSpec validation passed.
- All 12 bounded source reads succeeded under both old and new package revisions
  against the restored Subway MongoDB snapshots (24 checks). Each returned at most
  25 rows; companies returned two.
- A staged controlled-planner workflow received the new ontology/rule context and
  completed a real bounded read through existing Registry/runtime. No external
  model calls, source writes or outgoing actions were used. This does not verify
  live-model response quality; the user will test chat themselves.
- Public login and ontology pages passed for Subway and Simpsons at desktop
  1440×1000 and mobile 390×844. No page errors or horizontal overflow. Subway's
  28 candidate rules, nonempty source quotations and own business questions rendered.
- Live APIs verified both identities, ontology counts, compilation, historical
  versions and package revisions. Actual foreign source IDs return 404 in both
  directions. Subway coverage/questions do not load Simpsons reference material.

## Preservation and deployment

The installer appends version 2, its eight evidence documents, compiled artifacts and
package revision 2 in one Subway SQLite transaction, then updates Subway's configured
default package revision. It does not replace the live database with the staged DB.
Only Subway's backend was restarted, followed by the shared frontend; Simpsons'
backend PID was unchanged. Both dedicated services and the frontend were active.

Before/after fingerprints confirm existing workflows/revisions, runtime runs,
Google connections, metadata snapshots, credentials, original Subway version and
package revision 1 were preserved. Source connection fingerprints exclude volatile
profiling timestamps/status. Simpsons retains 79 concepts, 48 relationships and
eight rules. No client datasets were modified.

Private receipts and screenshots:

- `.local/tenants/subway/code-ontology-v2-final/`: reviewed code excerpts and artifacts.
- `.local/tenants/subway/code-ontology-stage/`: logs and workflow-verification.json.
- `.local/tenants/subway/code-ontology-preservation/before.json`: predeployment hashes.
- `.local/tenants/subway/code-ontology-release/`: installation/live/browser receipts,
  screenshots, predeployment SQLite backup and private backend environment backup.

To select the historical default again, stop Subway's backend, set only its
`BUILDER_SUBWAY_PACKAGE_REVISION` to 1 and restart it. This leaves both immutable
versions available. Restoring the full predeployment SQLite backup is only appropriate
while stopped and after checking for subsequent user changes; it would discard those
changes. Do not restore it over an active database.
