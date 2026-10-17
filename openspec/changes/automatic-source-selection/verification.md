# Automatic source selection verification

## Implemented behavior

Overview no longer exposes Input source or a manual/automatic selector. The requirement prompt always requests automatic setup inference. Additional links/details remain in that same prompt.

The canonical planning boundary replaces browser workspace-source evidence with bounded server reads scoped to the authenticated workspace and workflow.view permission. Current knowledge text and source references are supplied to the AI. Source candidates include published trigger resources, read targets, literal node inputs/mappings and previously discovered spreadsheet catalogs. Supported explicit spreadsheet references are inspected first and relevant saved references remain available. Unavailable optional references are reported; explicit reference errors remain safe errors. No resource access is granted by a source description.

At runtime, current saved knowledge is loaded from the accepted agent's Registry-owned workspace only when its accepted permissions include data.read. Ordinary calls, master decisions and delegated calls receive this as separate untrusted task data. Input schemas, registered instructions and executable grants are preserved. Actual offline CrewAI invocation verifies the knowledge reaches the model. URL-only sources are marked content_available=false and are never claimed as fetched content. Arbitrary URL fetching and new ingestion are not introduced. Context bounds and supported fields are documented in docs/automatic-source-selection.md.

Planning idempotency is checked before fresh source context is resolved, so updating knowledge does not invalidate the same retry key. Fresh planning requests and model invocations see updated knowledge.

## Verification

- Final complete frontend unit suite: **213 passed across 28 files**. The new test confirms no mode selector, unchanged prompt submission, automatic context and prompt retention on a safe error.
- Relevant planning/API/runtime/delegation/security/journey suites: **192 passed, 24 subtests**, 362 warnings, 95.70 seconds. This includes the initial eight source regressions. Subsequent source-catalog hardening was separately reverified below.
- Final focused source suite: **8 passed**, 6 warnings, 4.53 seconds, including actual offline CrewAI knowledge delivery, workspace isolation, permission denial, bounded evidence, source discovery, freshness and stable retries.
- Final isolated PostgreSQL source/API suite: **25 passed, 6 subtests**, 138 warnings, 24.84 seconds. A dedicated nonadministrative database/role was created and removed. No database dependency was skipped.
- Strict frontend types and lint pass. The isolated Next.js 16.4 production build passes, artifact **qPGCM9aYDKS2koDL1gx0W**. Contracts/fixtures and generated validator consistency pass.

The first new unit test expected a generic Error's raw message, but the UI intentionally sanitizes generic errors; the fixture now uses supported InputError and the full suite passes. The first browser diagnostic exposed one obsolete manual-mode setup expectation and was stopped after that failure; it is not counted as passing. Its compatibility case now explicitly creates the manual workflow through real canonical planning/save APIs while preserving branch, approval, persistence and unassigned-tool assertions. The overview and full new journey remain automatic. Final browser/deployment results are appended after completion.

## Boundaries

Models/provider transports in automated tests are offline; visual fixtures that mock APIs remain visual evidence. Production Google Workspace login/authenticated public lifecycle remains deferred. Supported product simulation remains unavailable. These existing production acceptance limits are not waived by this change. No real provider business operation, email, Sheets write or production workflow generation is submitted during release verification.

The next all-spec browser run exposed two desktop/mobile instances of a stale controlled-failure fixture: adding a required manual input to an automatic workflow correctly failed validation. The failure case now references an absent field in the actual master output. This preserves automatic input validation and still checks authoritative failed-node events, idempotent retry and preservation of the active prior revision. Its successful automatic lifecycle/execution steps had already passed; a clean final suite is required after the fixture correction.


## Final browser and live deployment result

The final complete default browser suite passed **all 55 scenarios** with the corrected explicit-session/manual compatibility fixture and automatic runtime failure fixture. All failed/partial diagnostics remain separate; none is counted as passing. The final run includes the real canonical automatic generation/review/edit/save/validate/approve/publish/activate/execute/failure/retry journey on desktop and mobile, and all existing delegation, permissions, traces, settings, Sheets panel and session recovery cases.

The exact tested frontend artifact **qPGCM9aYDKS2koDL1gx0W** was loaded into the running builder. The backend and worker were restarted to load source-context/knowledge changes. All three scoped services are active. Seven production source hashes match the checkpoint. Previous source originals and frontend artifact are retained with a prepared source/artifact rollback; rollback was not exercised. No migration or production business mutation was submitted.

**20 live HTTP checks passed**, including verified HTTPS/build identity, redirect, protected public endpoints, local authenticated proxy reads, private anonymous and invalid-origin rejection, bounded collections/events, invalid request parameters and active worker health. **Four live browser surfaces passed**: local desktop/mobile and public HTTPS desktop/mobile. Each confirms the input-source dropdown is absent, automatic-source guidance is visible and the requirement prompt is usable, with no page errors or broken assets. The public session remains correctly denied (403) pending Google Workspace login; this does not claim a public authenticated workflow journey. Live smoke did not generate, approve, execute, probe a provider, send email or write Sheets.

Evidence, screenshots, service identities and exact build/source checkpoints are retained under `.local/automatic-source-selection/`. Production readiness remains false for the existing deferred Google Workspace login and unavailable supported simulation.
