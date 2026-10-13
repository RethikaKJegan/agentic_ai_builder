# Connector extension verification — 12 October 2026

Added 17 canonical tool definitions in new files only: generalized multi-sheet reads/upserts and tab/header discovery; Calendar discovery/list/create/update/cancel; Gmail profile/search/message/thread/attachment/draft/send/reply; optional Brave search. Added a separate loopback API, OAuth helper, attachment staging and isolated UI launcher. Default provider enablement is empty.

- New offline Python suite: 53 tests passed, including generalized Sheets, Calendar, Mail and search coverage.
- Existing backend suite: 275 tests passed.
- Existing frontend suite: 90 tests passed; type checking and ESLint passed.
- Isolated production frontend copy: build passed.
- Actual unchanged UI connected to offline extension server: desktop and mobile browser scenarios passed.
- Existing canonical contract and fixture validation: passed.
- Generated frontend contract drift check: passed.
- Installed Python dependency consistency: passed.
- Strict additive-connector-extension OpenSpec validation: passed.
- All 484 pre-existing tracked files retain their exact starting SHA256 hashes.

Browser checks discovered all 17 tools, displayed truthful configuration-only readiness, executed a synthetic published Calendar workflow, paused before the provider write, approved through the existing UI, and observed completion. Python integration tests also execute actual Sheets writes and Gmail sends under canonical Registry/runtime approval, reject writes without dedicated gates, and inspect tool/handoff evidence. Provider calls are injected offline responses; no live Google, SMTP, Calendar or search action occurred.

The original launchers, database paths, credentials and session cookie are not reused for extension state. Browser fixture servers shut down after checks. No extension service is left running. Existing user code remains untouched. New implementation and OpenSpec files are uncommitted.

Operator setup remains: choose enabled providers, authorize the separate extension Google token, supply an optional Brave key, and deliberately start the new launcher/UI. Live OAuth/resource access, mailbox delivery and procurement business logic are not claimed by offline tests. See README.md for commands, provider references, bounds and remaining limitations.

## Generalized Sheets follow-up

Spreadsheet IDs and ranges are no longer required in extension configuration. With the Google connection enabled, read, discovery and workflow-bound write tools are available for user-selected links. Optional nonempty sheet_reads/sheet_writes lists remain extra restrictions; new sample configuration omits them.

41 extension tests passed. New cases cover different spreadsheet links, genuine header discovery (including header-only tables), Google access failures, optional restrictions, missing write grants, URL normalization without mutating saved workflows and separate approved write workflows for two different spreadsheets under one unchanged configuration. Both desktop/mobile browser cases discover 15 tools, generate a workflow from a new link, publish it and execute its read with offline providers. All 275 original backend tests and canonical contract/client/OpenSpec checks pass; all 484 original tracked files remain unchanged. No live account access, credential update or provider mutation occurred.

Evidence: .local/connector-extension/verification/generalized-sheets-*.log and generalized-sheets-preservation.json.

## Generalized connector follow-up

No spreadsheet, calendar, sender or recipient preset is required. Workflow inputs select account-accessible resources; Calendar discovery and Gmail profile expose actual connected-account metadata. Search accepts arbitrary queries and runtime country/language/freshness/page filters. Optional nonempty operator restrictions remain enforced, and provider writes still require exact workflow review plus a dedicated action approval. An extension-only Registry adapter retains independent reviewed workflows’ exact unexpired grants; the original public approval snapshot and explicit revocation semantics remain intact.

53 extension tests passed in 12.635 seconds. All 275 original backend tests and 90 original frontend tests passed, with type checking, lint, canonical contracts/client drift and strict OpenSpec validation. Both desktop/mobile browser cases passed in 15.5 seconds: they discover 17 tools, create/publish/read a workflow from a new spreadsheet link, approve a selected Calendar write and approve Mail to a new recipient with no resource or sender presets. Provider responses are offline fixtures; no live account operation is claimed. All 484 original tracked files remain unchanged.

Evidence: .local/connector-extension/verification/generalized-features-tests.log, generalized-features-existing-tests.log, generalized-features-browser.log and generalized-features-preservation.json. Existing extension tokens may require renewed Calendar-list consent via the separate helper.

## Live connector validation — 13 October 2026

The operator enabled Sheets, Calendar and Gmail, added a separate callback, and completed Google consent for Harihar. The token is private under extension state; original credentials/token remain unchanged. The opt-in backend runs on 8003 and an isolated production UI copy on 3002. Provider writes were reviewed and approved by the operator through the existing action approval UI.

- Sheets: actual discovery, reads from two native spreadsheets in one workflow, existing-record updates in both destinations and one new record were confirmed by read-back. The original spreadsheet's USB cable stock remains 5. The second test spreadsheet's Test cable stock remains 11 and its Test pump record is 2/1/5. Each spreadsheet has one tested tab; additional multi-tab scenarios are not claimed.
- Calendar: account discovery and event listing, creation, editing and deletion passed. The single created test event is now cancelled.
- Gmail: account profile, self-test send, search, plain-text message read, thread read, draft creation with a dummy attachment, reply within the original thread with that attachment and attachment download passed. Self-test messages remain in the mailbox and the unsent draft remains in Drafts.
- Attachment validation exposed actual long and rotating Gmail IDs. The extension-only schema now accepts bounded 4096-character provider IDs and uses stable MIME part references when available. Downloads resolve exactly one part within the requested message. 55 offline extension tests pass, including bounds, invalid inputs, refreshed IDs and wrong-part denial. The live downloaded 71-byte file matches the sent contents exactly.
- Brave search remains disabled and untested live until an operator supplies its separate key. Procurement business workflow development has not started.

All 484 original tracked file hashes remain unchanged. Strict OpenSpec validation passes. Evidence resides privately under .local/connector-extension/verification/live-*.json and attachment-id-tests.log. These live checks establish the specific tested operations, not universal provider behavior or all error/pagination scenarios. Previous offline verification above remains historical.

## Operator-driven procurement simulation — 13 October 2026

Read four requirements and four vendor rows from two supplied Sheets, created four reviewed RFQ drafts, sent four approved RFQs, read and checked four fictional quotations, and verified two approved simulation award replies and two PO attachments. Explicit supplier-stage emails advanced the Piping and Equipment orders through acceptance, packing, dispatch and delivery; explicit buyer receipt/resolution emails closed those two orders. Safety remains held for unverified certification, and the entire four-item project is not closed.

This uses separate single-operation connector workflows and a private JSON pilot ledger with session-performed comparison/state updates. No deployed autonomous procurement orchestrator, procurement SQLite store, unattended polling, source-sheet status synchronization or scheduled procurement reminders are claimed. Original project files remain unchanged. Full results and evidence: .local/connector-extension/procurement-pilot/pilot-results.md.

## Spreadsheet provisioning — Step 2, 13 October 2026

The catalog now contains 19 tools. New `extension_sheets_create` and `extension_sheets_add_tabs` are disabled by default and require explicit `sheet_creation_enabled: true`, Sheets edit consent, reviewed literal parameters and a dedicated action approval. They initialize literal headers, reuse compatible existing tabs without changing business rows, reject header conflicts and journal stable project setup keys across runs/restarts. Ownership receipts and read-only uncertain-result reconciliation are separate from the future procurement case database. The six-tab procurement helper returns proposed row-write targets; those proposals are not grants.

- 75 extension tests passed, including 20 new creation/recovery/approval cases.
- All 275 original backend tests passed.
- Desktop and mobile browser scenarios passed, discovering the new 19-tool catalog and exercising existing approval-driven Calendar/Mail and generalized Sheets read flows with offline providers. New creation approval behavior is covered through canonical runtime API tests; browser tests do not claim live creation.
- Step 1 domain fixture checks, canonical schemas/fixtures and generated client drift checks passed.
- Strict OpenSpec proposal and delta validation passed using the installed official validator library.
- All 484 original tracked files retain their Step 2 starting SHA256 hashes.

The live extension configuration has provisioning enabled, and only the isolated backend (8003) and UI (3002) were started. The existing extension Google token already has Sheets edit scope; no OAuth files were changed. Workflow `procurement_tracking_creation_check` is published and its run is **paused for human action approval** to create one spreadsheet titled “Agentic AI Builder procurement tracking test” with BOQ, Vendors, RFQs, Quotations, Orders and Activity. No live spreadsheet creation has occurred in this step yet. Procurement SQLite case persistence, automatic record synchronization and agent orchestration remain later steps.

Evidence: `.local/connector-extension/verification/sheet-creation-*.log`, `sheet-creation-preservation.json`, `live-sheet-creation-inputs.json` and `live-sheet-creation-pending.json`.

## Procurement persistence — Step 3, 13 October 2026

Added `connector_extension/procurement/store.py`, an explicitly initialized extension-only SQLite repository. Ten entity tables store current records; scoped identity, immutable revisions, ordered activity, durable transaction receipts, provider links and pending sync intents support audit and recovery. Schema/reference validation, expected revisions and BEGIN IMMEDIATE transactions prevent partial updates and concurrent lost writes. Guards cover BOQ scope digests, quotation arithmetic/currency/deadlines, current selection, approval expiry, monotonic quantities, supplier events, buyer-confirmed closure and actual project coverage. Production authority requires trusted callbacks; caller-supplied labels cannot establish approval or verified identity.

102 extension tests passed in 32.111 seconds, including 27 new persistence tests for restart/replay, concurrent revisions, rollback, namespace isolation, invalid transitions, duplicate messages/events, stale requirements, quote eligibility, holds, approval expiry/revocation, simulated closure and real-project authority denial. Step 1 fixture checks, shared canonical schemas/fixtures and generated client drift checks passed. Strict proposal/delta OpenSpec validation passed. All 484 original tracked files retain their Step 3 starting SHA256 hashes.

The separate `.local/connector-extension/procurement.sqlite3` was initialized with zero business records and SQLite integrity=ok. The earlier pilot JSON, original application database, workflow code, API routes, credentials and running services were unchanged. No Google operation occurred. The repository has no public API, deployed agent adapter, evidence parser, approval resolver or sync dispatcher yet. Full bid collection, amendments and provider reconciliation remain later integration work. See procurement/PERSISTENCE.md.

Evidence: `.local/connector-extension/verification/procurement-store-extension-tests.log`, `procurement-store-openspec.json` and `procurement-store-preservation.json`.

## Procurement first slice — Step 4, 13 October 2026

Added opt-in scoped procurement routes, two internal Registry tools, separate source/BOQ preparation specialists and a durable coordinator. A canonical source graph reads explicit requirement/vendor tables and maps actual outputs into deterministic ingestion. BOQ/context validation and section/category matching prepare durable READY RFQs; missing details stop before writes. Tracking creation, exact row projections and Gmail drafts execute only through normal canonical workflows and dedicated human action gates. The worker polls registered projects in bounded rounds and never decides approval.

116 extension tests passed in 112.082 seconds, including 14 new first-slice integration tests. The four-item stateful offline simulation created one six-tab tracking book, confirmed 12 BOQ/vendor/RFQ row projections and four Gmail drafts while leaving both source tables unchanged. It preserved draft IDs as unsent resources and RFQs as READY. Additional tests cover current-session permission denial, scope/plan mismatch, source graph tampering, missing quantities/categories/headers, specialist handoffs, worker advancement, rejection, durable transaction replay, restart of a pending run and unknown draft outcomes frozen without replay. All 275 original backend tests passed in 90.167 seconds. Domain fixtures, shared canonical schemas/fixtures, generated-client drift and strict OpenSpec proposal/delta checks passed. All 484 original tracked hashes are unchanged.

Only the idle isolated extension backend was reloaded, with no active/pending run at reload. The private extension configuration now enables procurement with INR precision 2 for the existing pilot currency, preserving Sheets/Calendar/Gmail settings. The unchanged isolated UI on 3002 shows 21 tools on desktop and mobile with zero page errors; the original 19-tool default catalog remains unchanged without opt-in. Authenticated live readiness checks verify the new routes and internal tools. There are zero live procurement jobs/business records, SQLite integrity is ok, and no Google operation was triggered by these readiness checks. No live end-to-end procurement success is claimed.

This slice uses deterministic registered tool nodes, not live model reasoning or document OCR. Calendar/order automation, quotation monitoring, email sending, approved amendments and stopped-project recovery remain later work. Actual live acceptance needs selected source mappings/context and exact action approvals. See procurement/AUTOMATION.md and setup.example.json.

Evidence: `.local/connector-extension/verification/procurement-slice-focused.log`, `procurement-slice-extension-tests.log`, `procurement-slice-original-tests.log`, `procurement-slice-openspec.json`, `procurement-slice-preservation.json`, `procurement-slice-live-readiness.json`, `procurement-slice-live-ui.json` and desktop/mobile screenshots.

## Live tracking creation and recovery — 13 October 2026

The operator authorized creation and reported the requested title absent in Drive after an uncertain first attempt. A controlled fresh, separately gated attempt retained the prior intent and exposed HTTP 400: sheet-level metadata was incorrectly placed in the spreadsheet root metadata list. The extension create payload now places root ownership metadata at the root and sheet ownership metadata on each respective sheet. The stateful offline Google fixture now rejects the invalid old structure, preventing this missed provider rule from recurring.

Added private bounded HTTP diagnostics and a scoped authenticated tracking-retry operation. Recovery preserves the old run/intent, requires an operator absence report or exact journal-confirmed HTTP 400 rejection, denies retry when an observed resource ID exists, limits fresh attempts and retains independent runtime action gates. No automated worker decides approval or retries uncertain effects.

All 122 extension tests passed in 102.360 seconds. Focused creation/recovery coverage passed 26 tests. Shared schemas/generated-client drift and strict OpenSpec proposal/delta validation passed. All 484 original tracked files remain unchanged. Original credentials/workflows were not modified. Only the idle isolated extension backend was reloaded.

The corrected live create completed and returned spreadsheet `1xJewVECc0XxiMB1Mf-EHFtlYBpsSVZJe810Et_cxh4Q`, titled “Automated four-item procurement simulation tracking”. Google read-back confirmed all six owned tabs and exact header manifests: BOQ (12), Vendors (6), RFQs (10), Quotations (17), Orders (18), Activity (9). Ownership and 12 exact projection intents are recorded in SQLite. The coordinator is now PROJECTIONS, paused before ITEM-001's initial row write. Zero tracking data rows or new Gmail drafts have been written yet; original source tables were only read. The earlier operator-driven pilot is untouched.

Evidence: tracking-metadata-fix-tests.log, tracking-recovery-extension-tests.log, tracking-recovery-preservation.json, procurement-live-slice-corrected-status.json, procurement-live-created-tracking.json and procurement-tracking-row-review.md under `.local/connector-extension/verification/`. Earlier unknown/rejected attempts remain in the effect journal and recovery history.
