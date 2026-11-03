# Verification — 3 November 2026

## Checks

- Full frontend suite: **455 passed in 70 files** (`/tmp/investigation-ui-final-unit3.log`). Types, full lint and staged Next build passed (`/tmp/investigation-ui-final-{types3,lint3,build3}.log`).
- Four final Playwright scenarios passed: desktop/mobile complete journeys, missing input/resume and failed generation without a forged graph (`/tmp/investigation-ui-browser-final3.log`). Screenshots inspected.
- Affected backend suite: **130 passed** covering jobs/service/graph, Phase 2 retrieval and KG integration (`/tmp/investigation-ui-backend-complete.log`). After the citation improvement, **57 passed**, including one new citation test (`/tmp/investigation-ui-backend-citations.log`). These overlap: **131 distinct cases**, not 187. This is scoped coverage, not a full repository backend suite claim.
- Shared contracts/fixtures, generated UI contract drift, strict scoped OpenSpec, Python compilation and diff integrity passed.

## Live acceptance

Confirmed Nginx routes the requested domain to this repository's frontend and API proxy. Built outside the live `.next`, retained old static assets, checked for active work before service restarts and preserved existing login/configuration. Final build: `ZOf2NBddrsZM1RGAcDDhL`; all three builder services active. InvestigationJobs runs under the existing worker supervisor.

Tested knowledge import on a private restored database, then explicitly imported live revision 6 as revision 7: `bov_331e7c5111a0f40324f20ff4d5e331e6`. Earlier snapshots remain byte-exact.

The public HTTPS browser used normal workspace sign-in. Unauthenticated `/api/backend/session` returned 401. Overview generated workflow `investigation_f98e3b40f26e2dd3e475dce5` from the real `A-2022-12-013` investigation prompt.

The initial run `investigation_run_9eaaed06f654511e86f1b9ce` failed after invalid model citation, correctly rejecting the finding. Added an explicit citation catalog and request-specific reference schema without automatic correction calls or relaxed validation. The failed run remains preserved.

Using **Start new run** produced `investigation_run_1086cbc0e461234dc4f13c56`, **completed_with_gaps**:

- 18 nodes, two conditions, 14 completed and four skipped.
- Three scoped retrievals, four observations representing two unique records.
- Three successful bounded CrewAI analysis calls; 25 validated findings.
- Missing evidence disclosed; coverage approval and physical identity remain unsupported.
- Verified actual node records, report source links, evidence drawer with collapsed technical data, readable zoom, refresh recovery and fresh mobile rendering. No browser runtime errors or horizontal overflow. Reopening the run did not add model calls.

Private receipts/logs/screenshots: `.local/investigation-ui-rollout-20261103/`. Browser fixture records are independently authored test values; real acceptance used connected Simpson records. Existing bounded evidence authorization was honored and response storage remains disabled.

## Preservation and limits

Created a consistent full SQLite backup plus source/configuration and frontend recovery artifacts before rollout. The preservation receipt checks encrypted source connections, existing policy heads/versions, business documents, earlier ontology snapshots, general workflow revisions and original runtime runs. Connection health/profile timestamps refresh normally; credentials/configuration remain unchanged. No company writes or general workflow dispatch occurred. Plans/runs/jobs and the explicit knowledge revision are authorized application-state writes.

Existing general automation remains available. This UI supports the backend's read-only investigation capability catalog, not arbitrary operational prompts. Authoritative policy/identity evidence and individual production authentication remain existing separate dependencies. Evidence uses existing persistence; no automatic retention cleanup was added.
