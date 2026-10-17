# Evidence

## Cause

The reported run `run_db641441c7734b19af17d47702e30230` was queued at 2026-10-17 13:55:14 UTC and failed at the `procurement_start` node at 13:55:15. The release for its exact revision was created at 13:56:45 UTC, over a minute later. The previous Start button required publication but not activation. Its connector raised ProcurementError for the inactive release and the graph mapped that exception to INVOCATION_FAILED. The current reviewed plan also passed offline setup preflight before database access. No spreadsheet-specific workaround is warranted.

## Change

- Runtime admission calls a trusted optional execution validator before inserting a new run. Procurement registers an exact active-release check; other workflow types retain their existing behavior. The check shares the run transaction and verifies the release workspace.
- StartConnector rechecks activation at invocation and preserves safe setup domain error codes rather than replacing them with INVOCATION_FAILED.
- The Start control checks authoritative release state, explains missing activation, refreshes readiness and rechecks before submission.
- The UI start key is stable per release, preventing duplicate submissions and avoiding reuse of the old pre-activation failed run key. It does not include prompt or spreadsheet constants.

## Validation

- Final focused backend suite: 6 passed (missing/disabled/wrong-revision/other-workspace releases rejected without queued runs or project effects; activation race and setup failure retain specific error codes).
- Broader backend run: 78 test executions and 18 subtests passed. The initial collection included nine inherited procurement tests twice before the test import was corrected; this is not 78 distinct tests. The corrected focused file collects exactly six tests and its final run passed separately.
- Frontend: 219 tests passed; TypeScript and targeted ESLint passed.
- Shared contract schemas and fixtures passed, with no contract edits.
- Isolated production build passed, BUILD_ID `dgz451Wosu1m50bh5KOu6`.
- Desktop/mobile production browser checks with mocked APIs passed: inactive Start blocked, activation refresh enables Start, exactly one execution request carries the stable release key and empty inputs; no page errors.
- Deployed by gracefully stopping the existing worker, reloading the backend and replacing only the frontend artifact, then resuming the worker. All three services active with zero automatic restarts. The previous frontend build is preserved under `.local/procurement-start-readiness/previous-next`.
- Read-only live HTTPS checks of the exact reported workflow passed at 1440 and 390 pixels: revision 2 active, updated activation instructions loaded, Start enabled, no browser page errors. Screenshots and measurements are under `.local/procurement-start-readiness/`.

No live procurement retry, email send, spreadsheet write, credential change, workflow regeneration or publication was submitted during verification. The original failed run remains historical; live end-to-end RFQ delivery after this change has not been exercised.
