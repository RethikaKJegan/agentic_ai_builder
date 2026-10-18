# Whole-app acceptance and stability test guide

Prepared against repository source on 18 October 2026 (IST). This is a test plan,
not a completed acceptance report. Every case starts **NOT RUN** in
`whole-app-results.csv`. The public app is
<https://praxi.bellcorpstudio.com/app>.

## 1. Prepare before testing

1. Use an isolated test deployment/database for edits, approvals, runs, account
   disconnects, credential changes, failure injection, restarts and load tests.
   Read-only browsing can be done on the public app. The currently documented
   shared demo subject does not establish separate per-person accounts: separate
   browsers alone are not an authorization isolation test.
2. Label all test records `QA-<date>-<unique suffix>`. Record the app build ID,
   environment, browser/version, OS/version, tester, account and start time.
3. Prepare authorized test identities for viewer, editor/builder, approver and
   administrator, and a second workspace in the isolated environment. If these
   identities are unavailable, mark the relevant cases **BLOCKED**. Do not change
   browser role flags to simulate backend authorization.
4. Prepare two Google test accounts A/B, dedicated Sheets and calendars, controlled
   sender/recipient inboxes, and a dedicated Slack test workspace if testing Slack.
   No real customers/suppliers should receive test messages. Provider/model tests
   can incur charges. Use only approved test resources and recipients.
5. Prepare Northwind test PostgreSQL/MongoDB connections. Keep the working seed
   file intact. Prefer a copy of the data for relationship edits and failure tests.
6. Back up the test app store, auxiliary stores, configuration and encryption keys
   using the operator's supported consistent backup procedure. Verify restoration
   separately. Do not copy a live SQLite database file alone and assume consistency.
7. Open DevTools on desktop: Console and Network, with Preserve log enabled. Do
   not export unredacted cookies, authorization headers, connection URIs, OAuth
   callback URLs or query results into bug reports.
8. Run sections in order. Finish the basic read-only pass before writes, then run
   recovery and load checks after functional behavior passes.

**Results:** PASS = expected behavior observed; FAIL = a defect; BLOCKED = missing
authority/configuration/dependency; NOT RUN = untested. An intentionally disabled
action passes when its explanation and server rejection are correct. It does not
make the unavailable feature implemented. Recheck failed cases after a fix and
repeat the related regression cases.

For every row record actual behavior, exact workflow/revision/run/job IDs when
relevant, safe request/correlation ID, timestamp and screenshot/trace reference.
The CSV contains blank fields for these. A test row with several named controls
requires checking **each** control; duplicate the row into subrows if outcomes differ.

## 2. Apply this checklist to every interactive control

For every button, link, menu item, tab, input, switch, slider, dropdown and dialog:

1. Open its parent screen and verify label, value, current state and explanation.
2. Exercise the normal action; verify its actual destination/state/result.
3. Try empty, whitespace, invalid, boundary-length and valid values where relevant.
4. Repeat rapidly while a request is pending. Conflicting actions must be disabled
   or safely deduplicated; no extra workflow, run, job or external write should occur.
5. Exercise Cancel/Close/Escape and any destructive confirmation. Cancellation
   before submission must not perform the action.
6. Refresh and reopen the screen. Verify persistence according to the feature:
   browser draft, saved server revision or intentionally temporary UI state.
7. Repeat with insufficient server authority. Verify the API also rejects the
   request; a hidden button alone is not access control.
8. Exercise failure/retry in the isolated environment. Preserve user input and
   confirmed data, display a safe actionable error, and do not show false success.
9. Check keyboard operation/focus and repeat on mobile, including a visible keyboard.

`source-controls.csv` inventories current source controls with file/line, label,
handler and disabled expression; it also starts NOT RUN. It includes shared UI
primitives and loop expressions. Expand each runtime-generated menu, node kind,
pattern, model, integration operation and filter option. A source inventory is
not proof of test coverage, and an unused primitive is not a product feature.

## 3. Startup, website and shared shell

Read-only cases can run on the public app. Editing/failure cases require the test environment.

| ID | Steps | Expected result |
| --- | --- | --- |
| SHELL-01 | Open `/`, follow each visible website link and CTA, then enter the app. | Correct real destination; no dead controls, blank screen or invented completed action. |
| SHELL-02 | Test landing animation normally, with reduced motion and with WebGL unavailable. | Usable content and navigation in all cases; a capability fallback is acceptable. |
| SHELL-03 | Open each route directly: `/app`, `/app/workflows`, `/app/agents`, `/app/marketplace`, `/app/integrations`, `/app/data-intelligence`, `/app/knowledge`, `/app/approvals`, `/app/runs`, `/app/monitoring`, `/app/governance`, `/app/settings`. | Correct screen loads without an endless skeleton; permission errors are explicit. |
| SHELL-04 | Refresh each route; test browser Back/Forward and opening a direct link in a new tab. | Correct route/state; no unrelated mutation or duplicated record. |
| SHELL-05 | Expand/collapse desktop sidebar; use breadcrumbs, logo, Create workflow and Back to website. | Navigation/layout remain usable at each width. |
| SHELL-06 | Open search, type matching/nonmatching text, select every result category, dismiss and reopen. | Correct destinations/empty state; Escape and keyboard selection work. |
| SHELL-07 | Exercise Ctrl/Cmd+K, `?`, and displayed G-then-key shortcuts outside inputs; repeat while typing. | Shortcuts work where appropriate and do not steal typed text. |
| SHELL-08 | Open notifications and user menu; inspect activity links and pending-approval link if present. | Correct records and destinations; empty data is clearly empty. |
| SHELL-09 | Open mobile More; visit every destination, dismiss, rotate and reopen. | Menu works, selected route is correct, content remains accessible. |
| SHELL-10 | In an isolated browser test, load a previous build's captured HTML after a new build is deployed. | All referenced retained JS/CSS loads; the app hydrates. No missing chunk 404s. |
| SHELL-11 | Open an invalid route and a nonexistent workflow ID. | Not-found/safe error screen; navigation back works. |

## 4. Overview, planning and source discovery

Use a test Google Sheet with headers `product, actual_stock, reorder_threshold,
target_stock` and rows `Pen,5,10,25` and `Book,20,10,25`. Use this read-only objective:

```text
When manually started, read [TEST SHEET URL], range Inventory!A1:D100.
The headers are product, actual_stock, reorder_threshold, target_stock.
Report products below the reorder threshold and calculate target_stock minus
actual_stock as the requested restock quantity. Use fresh connector evidence.
Do not send emails or modify any spreadsheet.
```

Review the generated plan; do not assume the planner produced an executable plan
merely because it returned a diagram. Missing setup must block publication.

| ID | Steps | Expected result |
| --- | --- | --- |
| PLAN-01 | Submit an empty/whitespace objective, then a valid objective. | Invalid input is rejected; valid input produces a reviewable draft or a specific setup/model error. |
| PLAN-02 | Run the example objective using automatic source selection. | Correct accessible Sheet/tab/headers selected; setup evidence is real, not invented. |
| PLAN-03 | Open a prepared QA canonical workflow declaring manual text, integer, number, boolean, array and object inputs; inspect its review. | Declared inputs/mappings match the fixture. Current Overview requests automatic input mode; do not look for a separate manual-input chooser there. |
| PLAN-04 | Supply an ambiguous Sheet with multiple plausible tabs. | Clarification/setup requirement; no guessed business source. |
| PLAN-05 | Supply an inaccessible/nonexistent Sheet and a malformed URL. | Safe resource/input error; no substitute account or invented rows. |
| PLAN-06 | Inspect review goal, inputs, triggers, outputs, steps, branches, responsibilities, tools and gates. | Review agrees with the saved canonical draft and the requested objective. |
| PLAN-07 | Choose Review and edit workflow, return, and explicitly regenerate. | Draft remains recoverable; regeneration requires its explicit choice. |
| PLAN-08 | Repeat a prompt that resolves to the same existing identity while it has dirty local edits. | Existing revision is identified; dirty edits are not silently overwritten. |
| PLAN-09 | Double-click generation; inject a model timeout/invalid response in staging and retry. | No uncontrolled duplicate submission; prompt survives and errors remain actionable. |
| PLAN-10 | Inspect recent workflows, View all and available workflow pagination. | Correct records/pages without repeats or false empty results. |
| PLAN-11 | Start QA generation, note its planning job ID, then use Cancel generation while queued/running. | Cancellation reaches its recorded state and discards an eligible result; already incurred model usage cannot be undone. |
| PLAN-12 | Refresh/navigate away during QA generation and inspect the recorded job/saved draft before retrying. | No automatic duplicate submission. Record any missing UI recovery as a usability gap; query-job restoration does not prove planning-job restoration. |

## 5. Workflow list and design editor

| ID | Steps | Expected result |
| --- | --- | --- |
| EDIT-01 | Search and exercise every displayed workflow filter; test matching/nonmatching values. | Correct matching records and truthful empty state. |
| EDIT-02 | Use available New/Create control; open a saved workflow and return to the list. | Correct workflow opens; local versus saved state is clear. |
| EDIT-03 | Rename a QA workflow; refresh before saving and after Save draft. | Local edit survives supported draft recovery; confirmed save persists the server name/revision. |
| EDIT-04 | Open Design, Agent hierarchy and Execution; return to Design. | Views remain distinct; execution evidence does not overwrite the editable graph. |
| EDIT-05 | Add each node kind offered under Add step, one at a time. | Correct inspector and node kind; local graph updates without claiming server validation. |
| EDIT-06 | Select, drag and reconnect nodes; use zoom, fit view, minimap and Auto-layout. | Readable graph; supported positions survive saving/reloading. |
| EDIT-07 | Undo/redo add, edit, delete, edge change and a complete node drag. | Correct prior/final state; drag undo restores the pre-drag position. |
| EDIT-08 | Insert every available pattern and reuse an existing agent. | Expected nodes/edges/agent reference; no accidental duplicate IDs or grants. |
| EDIT-09 | Edit step name/instructions and applicable trigger/tool/input/output configuration. | Draft changes appear in the correct node; unrelated steps remain unchanged. |
| EDIT-10 | Edit a condition expression/outcome names and branch connections. | Directed labels match outcomes; invalid/missing branch mappings fail validation. |
| EDIT-11 | Use keyboard connection/removal, Delete, F and Escape; repeat in mobile step-outline mode. | Same graph semantics; inputs do not trigger destructive shortcuts. |
| EDIT-12 | Try a dangling edge, unsupported configuration, disconnected required step and invalid graph. | Local diagnostics/server validation identify the problem; no false publish success. |
| EDIT-13 | Delete a step/workflow in a disposable fixture; first cancel, then confirm. | Cancel preserves it; confirmed deletion follows scope and preserves required server history. |
| EDIT-14 | Duplicate a workflow; change its agent instructions and graph. | Source workflow/agents stay unchanged; copy starts as an unapproved local draft. |
| EDIT-15 | Open Workflow details and saved revision history; inspect an older revision. | Exact historical revision is read-only and does not replace current edits. |
| EDIT-16 | Attempt to navigate away, use Back or reload with unsaved edits. | Supported warning/recovery behavior; no silent loss of a dirty working copy. |

## 6. Synchronization and conflicts — use two tabs in staging

| ID | Steps | Expected result |
| --- | --- | --- |
| SYNC-01 | Open the same QA revision in tabs A/B. Save a clean newer revision in A; focus B. | B reconciles newer confirmed state without downgrading it. |
| SYNC-02 | Make unsaved changes in B; save different changes in A; focus B. | B retains its draft and displays conflict evidence. |
| SYNC-03 | Inspect loaded/remote documents and export the working draft. | Export contains recoverable working graph/agent data; no forced save occurs. |
| SYNC-04 | Choose keep this tab's draft; refresh B. | Supported tab recovery retains B's edits; it does not grant server overwrite authority. |
| SYNC-05 | Rebase nonoverlapping edits, then save. | Combined draft is reviewable; Save uses the new base revision. |
| SYNC-06 | Rebase overlapping edits and deletion-versus-change conflicts. | Conflict is refused/explained; neither side silently wins. |
| SYNC-07 | Cancel Reload server revision; then confirm it on a disposable draft. | Cancel preserves edits; confirmed reload replaces only the intended working state. |
| SYNC-08 | Edit while save/reload is in flight using throttled staging requests. | Later local edits remain dirty and are not erased by an older response. |
| SYNC-09 | Block storage writes in an isolated browser profile and edit. | Storage failure is visible with recovery/export guidance; no false backup claim. |
| SYNC-10 | Lose a save response after server acceptance; reopen and inspect the revision. | Confirmed saved revision can be discovered; no blind duplicate write/replay. |

## 7. Workflow lifecycle — each transition separately

| ID | Steps | Expected result |
| --- | --- | --- |
| LIFE-01 | Save a QA draft; inspect timestamp/version and reopen it. | Exact server-confirmed revision persists. |
| LIFE-02 | Validate a valid and invalid saved revision. | Real validation evidence or exact field/Registry blockers. |
| LIFE-03 | Request an unregistered tool, unauthorized resource or changed unaccepted agent configuration. | Registry blocks it; browser edits cannot create executable grants. |
| LIFE-04 | Submit a clean validated, Registry-ready revision for approval. | Exact revision appears for review; submission alone does not approve/publish it. |
| LIFE-05 | Approve with eligible identity, then attempt with an unauthorized identity. | Eligible exact revision can advance; unauthorized request is denied by the server. |
| LIFE-06 | Publish the approved clean revision. | Published revision advances independently; Publish does not silently Save/Approve/Activate. |
| LIFE-07 | Activate using its confirmation; inspect release ID/state and trigger bindings. | Exact published revision is activated or a clear provider/setup blocker appears. |
| LIFE-08 | Edit after publishing/activation, then save a newer draft. | Existing release remains on its original revision; new draft needs fresh review. |
| LIFE-09 | Double-click/retry save, submission, approval, publication and activation with the same payload. | At most one intended transition/effect; uncertain outcomes stay explicit. |
| LIFE-10 | Disable a test release; inspect history and try a new trigger event. | New effects stop under server policy; prior history remains. |
| LIFE-11 | Open lifecycle progress and expanded guidance at each stage. | Current draft, published revision and active release are distinguished accurately. |
| LIFE-12 | Inspect simulation controls, if shown. | Explicitly unavailable without a supported adapter; validation is not presented as simulation. |

## 8. Agents, hierarchy, tools and communication

| ID | Steps | Expected result |
| --- | --- | --- |
| AGENT-01 | Create a local agent and edit General name, role, purpose and instructions. | Correct local agent changes; backend-controlled names remain protected where disabled. |
| AGENT-02 | Select each offered model, adjust temperature, open Advanced and edit token limit/output schema. | Correct draft values; availability/authorization is still checked by backend. |
| AGENT-03 | Exercise available fallback/memory settings; submit invalid schema/budget values. | Unsupported/backend-controlled options stay disabled; invalid execution configuration is rejected. |
| AGENT-04 | Inspect requested capabilities, assigned tools, permissions, risk, availability and approval state. | Requests and actual authorized assignments remain distinct. |
| AGENT-05 | Open Knowledge and Safety tabs; try available associations/guardrails. | Honest draft/unavailable state; no invented ingestion or runtime enforcement. |
| AGENT-06 | Pause/resume a local agent and change local budget/approval controls. | Draft-only effect is clear; do not infer that an already-running server agent stopped. |
| AGENT-07 | Inspect master/child hierarchy, navigate parent/children and delegated templates. | Ownership/responsibilities/tool review match canonical configuration, including templates without graph nodes. |
| AGENT-08 | Open Agent communication with no run, then choose a recorded run. | Planned topology and recorded runtime evidence are visibly different. |
| AGENT-09 | Inspect diagram/evidence views, node selection, expanded evidence, layout/reset/fit controls. | Actual handoff/tool evidence is linked to the correct run/revision; no invented completion. |
| AGENT-10 | Execute a QA master/specialist workflow with multiple tasks; inspect delegation and synthesis. | Results use actual recorded specialist/tool outputs; task ownership and cumulative findings stay consistent. |
| AGENT-11 | Switch runs while communication is open; inspect a historical agent revision. | Dialog remains usable and historical evidence uses historical agent configuration. |

## 9. Runs, inputs, execution traces and approvals

Use the reviewed read-only inventory workflow above. Its expected finding is Pen,
restock quantity 20; Book should not be marked below threshold. Verify actual
connector evidence and model reasoning, not just the final prose.

| ID | Steps | Expected result |
| --- | --- | --- |
| RUN-01 | Open Run published for a QA manual workflow. | Dialog uses the published revision, not a dirty/newer draft. |
| RUN-02 | Test required/optional fields, integer versus fraction, finite number, explicit false, JSON array/object and invalid JSON/null. | Exact input validation; optional blanks omitted; false is not treated as missing. |
| RUN-03 | Cancel the run dialog before submit; reopen and submit valid inputs. | Cancellation creates no run; confirmed submission exposes the actual run ID. |
| RUN-04 | Double-click Run; drop a staging response and explicitly retry unchanged inputs. | No duplicate intended run; safe stable retry identity and unknown-outcome handling. |
| RUN-05 | Inspect Runs filters: workflow, status and displayed date boundaries; Older/Newest pages. | Filtering precedes paging; no duplicate/missing page records from new inserts. |
| RUN-06 | Open a direct `/app/runs?run=ACTUAL_ID` link, then refresh. | Exact run and revision remain selected. |
| RUN-07 | Inspect queued/running/paused/success/failed/blocked/cancelled states using fixtures. | UI reflects persisted evidence; missing events remain unknown rather than fabricated success. |
| RUN-08 | Inspect node inputs/outputs, safe failures, retry history, timing and actual recorded branch path. | Evidence matches the selected run; credentials and raw stacks are not exposed. |
| RUN-09 | Select an old run after editing the current design. | Exact historical topology is read-only; current edits remain intact. |
| RUN-10 | Load additional event pages and refresh/reconnect during execution. | Ordered deduplicated events resume from confirmed sequence without gaps/conflicting identities. |
| RUN-11 | Wait for terminal state, then inspect network polling and use explicit Refresh trace. | Automatic selected-run polling drains remaining events then stops; explicit refresh works. |
| RUN-12 | Trigger a QA action gate. Inspect preview and approve; repeat with reject/timeout fixtures. | Exact allowed decision is recorded; rejection/timeout does not execute the gated write. |
| RUN-13 | Decide a gate without its required role/workspace permission; retry an already-decided gate. | Server rejects unauthorized/conflicting decisions; no duplicate effect. |
| RUN-14 | Run the read-only inventory workflow and independently compare the Sheet. | Pen/20 finding is supported; source Sheet is unchanged and no email is sent. |

## 10. Integrations and Google account management

| ID | Steps | Expected result |
| --- | --- | --- |
| INT-01 | Open each integration card and Check configuration. | Not configured, configured-not-verified, verified and failed states reflect real evidence. |
| INT-02 | Try unsupported connectivity probes; run the installed SMTP verification only on an approved test account. | Unsupported probes are explicit; SMTP check does not send MAIL/RCPT/DATA. |
| INT-03 | Connect Google with selected capabilities; complete consent using test account A. | Callback returns the actual account and granted scopes; successful navigation alone is insufficient. |
| INT-04 | Cancel consent; test denied consent and expired/replayed callback in isolation. | No false connected state or account replacement. |
| INT-05 | Verify account, refresh and reopen Integrations. | Persisted account remains; verification checks identity/token health, not every service permission. |
| INT-06 | Manage access and grant an additional capability to the same account. | Actual returned scopes displayed; unticking alone is not represented as Google revocation. |
| INT-07 | Connect B; select A/B before generation and in revision account binding. | Distinct records/bindings; changing a binding creates a reviewable draft revision. |
| INT-08 | Use B against a Sheet accessible only to A. | Access fails under B; no fallback to A or legacy credentials. |
| INT-09 | Disconnect/reconnect a test record and attempt new operations while disconnected. | New resolution is blocked; correct account is required for reconnection. |
| INT-10 | Inspect errors/API/browser storage with safe test credentials. | No token/URI/password leakage; callback details are not included in test reports. |

If Google reports `redirect_uri_mismatch`, record a configuration blocker with
the operator. Do not change consent settings or pretend the account connected.

## 11. Every installed Google tool operation

In Integrations → **Test Google tools with a workflow**, select a test account,
choose an operation, replace every placeholder with a real test resource and
click **Create tool-check draft**. Review, validate, approve, publish and run using
the normal lifecycle. Approve writes only where the saved policy requires it.
An operation missing from the installed/enabled list is BLOCKED/not installed,
not a passed operation. Repeat the normal/failure checks for **every listed operation**.

| ID | Steps | Expected result |
| --- | --- | --- |
| TOOL-01 | Create a tool-check draft without running it. | Draft only; no email, calendar event or Sheet write. |
| TOOL-02 | Read/discover a test Sheet with known headers/rows. | Correct account/resource/tab/values; no source mutation. |
| TOOL-03 | Create a test spreadsheet and add a test tab where installed. | Actual returned resource IDs exist in the selected account; no unrelated document changes. |
| TOOL-04 | Upsert a known test identity; repeat; update an allowed field. | One identity row, correct allowed cells, unrelated columns unchanged. |
| TOOL-05 | Try duplicate headers/identities, forbidden fields, full range and missing update-only identity. | Specific safe failure; no guessed match or unauthorized write. |
| TOOL-06 | Gmail search, message read and thread read against known test messages. | Correct IDs/content/account; distinguish Gmail API ID from RFC Message-ID. |
| TOOL-07 | Create a draft; explicitly send to an approved test inbox. | Draft/Sent records and recipient evidence checked separately; API acceptance is not inbox delivery proof. |
| TOOL-08 | Reply to a test message and inspect thread association. | Correct selected account, recipient and thread; no unrelated conversation modified. |
| TOOL-09 | List Calendar events; create, update and cancel one future timezone-aware test event using its returned ID. | Correct calendar/timezone/event lifecycle; invitations are not expected where sendUpdates=none. |
| TOOL-10 | Retrieve an attachment through an installed supported workflow tool. | Authorized artifact and bounded handling; do not expect a separate upload UI. |
| TOOL-11 | Remove a scope or use an unauthorized resource/recipient in staging. | Explicit scope/resource denial; consent does not override destination allowlists. |
| TOOL-12 | Inspect Google account used in the recorded node trace for every tool check. | Provenance matches the immutable workflow revision/account binding. |

## 12. Event automation, Sheets writes, Slack and customer replies

| ID | Steps | Expected result |
| --- | --- | --- |
| AUTO-01 | Activate a test new-row Sheet workflow with existing rows. | Baseline completes without running every preexisting row. |
| AUTO-02 | Append one fresh unique row; inspect readiness, dispatch and run. | One intended event/run after configured polling and processing latency. |
| AUTO-03 | Reprocess/restart with the same completed identity; append a distinct identity. | Completed identity is not duplicated; new identity is processed. |
| AUTO-04 | Edit an existing baseline row for a new-row-only trigger. | It is not silently treated as a fresh new-row event. |
| AUTO-05 | Exercise reviewed Followups/source-status upserts on test Sheets. | Only intended rows/cells change; duplicate/retry does not append another logical record. |
| AUTO-06 | Cause the second write of a two-target operation to fail in staging. | Partial external success is reported honestly; no claim of a cross-service rollback. |
| AUTO-07 | Send a valid event in a dedicated Slack test workspace, then deliver its duplicate. | Authorized mapped event is handled once; no unrelated workspace event accepted. |
| AUTO-08 | Disconnect/misconfigure the test event source and disable its release. | Safe health/setup failure; disabled release creates no new effects. |
| AUTO-09 | Open Runs → Customer replies; refresh an empty, populated and failed case list. | Empty versus failed is distinct; source/case identity and monitor state are correct. |
| AUTO-10 | Reply to a controlled customer thread; inspect follow-up/manager/closure previews. | Correct case/thread/sender matching and actual cumulative findings. |
| AUTO-11 | Approve each offered reply action with eligible authority; repeat while busy. | Intended action once; no duplicate message on repeat. |
| AUTO-12 | Test automatic routine follow-up under a published automatic email policy. | Automatic behavior follows that reviewed policy; do not require a gate the policy intentionally omits. |
| AUTO-13 | Send ambiguous thanks, then explicit resolution evidence in a controlled thread. | Thanks alone does not close the case; closure needs policy-required evidence. |
| AUTO-14 | Try a wrong sender/thread or unauthorized closure action. | No unrelated case modification or role bypass. |

For full configured Sheet/customer examples, use `../sheet-drafts-phase1.md`,
`../prompt-only-automation.md` and `../automatic-customer-workflows.md`. Their
configuration requirements and effect limits still apply.

## 13. Procurement — simulation/test project only

This automated procurement adapter is documented for simulation. It is not proof
of real-world supplier, delivery or procurement authority. Use disposable BOQ and
vendor Sheets, controlled mailboxes and future dates. Do not reuse the dated
example's old deadlines blindly or send its named recipients mail.

| ID | Steps | Expected result |
| --- | --- | --- |
| PROC-01 | Generate/review a test procurement objective with real test BOQ/vendor source structure. | Correct source/column roles, requirements, policy and setup blockers. |
| PROC-02 | Inspect process overview and Edit underlying graph; return. | Both views describe the same QA project without changing recorded history. |
| PROC-03 | Review proposed suppliers and explicit approval/automatic action mode before activation. | Supplier coverage/review is real; mode is visible and respected. |
| PROC-04 | Activate/run the QA project and inspect RFQs in controlled inboxes/tracking workbook. | Correct line items, vendor targets, deadlines and child-action evidence; no duplicate RFQs. |
| PROC-05 | Submit qualifying competing quotes in each correct RFQ thread. | Sender, currency, quantities, specifications, price and delivery evidence are captured accurately. |
| PROC-06 | Submit incomplete, incompatible, late or ambiguous quotation evidence. | Clarification/rejection as applicable; no fabricated qualifying offer. |
| PROC-07 | Inspect recommendation, permitted award decision and resulting POs. | Per-item reasoning and saved policy support awards; actual PO IDs and recipients match. |
| PROC-08 | Activate fulfilment on existing QA POs with separate buyer and manager contacts. | Existing POs reused; RFQs/awards/POs are not resent. |
| PROC-09 | Send acceptance, packing, dispatch and delivery one stage at a time; refresh after each. | RELEASED → ACCEPTED → PACKED → DISPATCHED → DELIVERED with genuine Activity evidence. |
| PROC-10 | Test cumulative/additional partial quantities, regressions, over-quantity and missing/out-of-order stages. | Truthful partial state or clarification; no invented stage/quantity. |
| PROC-11 | Have the supplier report delivery without buyer confirmation. | Order stays open; separate buyer receipt request is tracked. |
| PROC-12 | Confirm full receipt/acceptance/resolution from the configured buyer for each PO. | Each PO closes independently; project completes only when all required items are covered. |
| PROC-13 | Report shortage/damage/delay, resolve through the eligible buyer, and test a commercial change request. | ON_HOLD/exception evidence, correct review authority, no automatic price/substitution authorization. |
| PROC-14 | Test reminder/escalation timing with short staging-only policy intervals. | Bounded intended reminder/escalation effects; no duplicates after refresh/restart. |
| PROC-15 | Inspect Orders/BOQ/Activity, manager notice and Calendar events by actual PO ID. | Values, timezone and status updates match evidence; supplier delivery alone never means CLOSED. |
| PROC-16 | Inspect project communication before a root run and across child actions; disable the parent. | Actual project/child evidence remains accessible; disabled parent stops new effects. |

Detailed staged email examples are in `../procurement-full-test-6.md`; replace
every identity, date, resource and recipient for this test. Messages labeled
SIMULATION are still real emails when sent through real accounts.

## 14. Marketplace, Knowledge, Governance and Settings

| ID | Steps | Expected result |
| --- | --- | --- |
| OTHER-01 | Search Marketplace, test all category tabs and Workspace library only. | Correct matching assets and no-results state. |
| OTHER-02 | Open every asset type and preview template/agent/guardrail details. | Correct description, configuration and applicable action. |
| OTHER-03 | Add a workflow template and agent draft; follow Open; repeat an install. | Editable local drafts/appropriate repeat semantics; no false backend authorization. |
| OTHER-04 | Try connector/guardrail catalog actions. | Only implemented draft/configuration behavior occurs; no invented live connection/enforcement. |
| OTHER-05 | Open Knowledge and Refresh sources with populated/empty/failed responses. | Persisted sources or explicit empty/error; ingestion remains unavailable in this UI. |
| OTHER-06 | Open each Governance tab: Draft agent controls, Enforced governance & usage, Draft policies, Draft rules, Draft audit log. | Local drafts and live server evidence are clearly separated. |
| OTHER-07 | As an authorized staging admin, edit local budgets, policy/rules, toggles and delete confirmations. | Local draft/audit changes only; active published revision is not silently changed. |
| OTHER-08 | Repeat governance edits without server admin authority. | Controls/requests respect current authorization; local role changes confer none. |
| OTHER-09 | Compare enforced policy/revision scope, usage and cost/call/token counters to actual QA runs. | Correct scope and recorded evidence; unavailable measurements are not invented. |
| OTHER-10 | Open Settings, wait for confirmed load, edit Notification preference, Save setting and reload. | Confirmed server persistence/timestamp; preference alone does not create notification delivery. |
| OTHER-11 | Test unchanged save, failed load/save, >2000 characters and secret-like text. | No overwrite of unknown state; validation/error preserves previous value and current input. |
| OTHER-12 | Cancel then confirm Reload settings with unsaved input; test nonadmin save. | Correct discard behavior; server denies unauthorized mutation. |

## 15. Data Intelligence connections and metadata

| ID | Steps | Expected result |
| --- | --- | --- |
| DATA-01 | Connect a test PostgreSQL source: name, URI, database, northwind schema, mode and optional description. | Test succeeds before Connect and profile is enabled; saved connection queues discovery. |
| DATA-02 | Repeat with MongoDB Atlas using its actual test database/allowed network access. | Correct engine/database and real profiling state. |
| DATA-03 | Test wrong password/host/database, invalid URI, certificate/network failure and each supported connection mode in fixtures. | Specific safe failure; no saved false-connected record or insecure certificate bypass. |
| DATA-04 | Inspect queued/running/ready/failed profiling and retry/refresh. | Last successful snapshot and current job state are distinguished; no invented completion. |
| DATA-05 | View each dataset/field/type/nullability, index, constraint and declared key. | PostgreSQL metadata matches actual declarations; Mongo sample coverage is labeled. |
| DATA-06 | Inspect Mongo validation rules, mixed/optional fields, empty collection and empty schema fixtures. | Truthful discovery/coverage warnings; omitted samples do not prove deletion. |
| DATA-07 | Refresh unchanged metadata; change a test field/index and refresh again. | Revision/change summary reflects actual supported discovery differences. |
| DATA-08 | Update credentials for a disposable connection; cancel first, then save/profile. | Correct generation/reprofiling; password is not returned or stored in browser storage. |
| DATA-09 | Disconnect a disposable source; inspect metadata/relationships and attempt a new query. | Disconnected source stops being current query authority; saved business rows remain unchanged. |
| DATA-10 | Repeat connection/build/edit actions as a read-only identity. | Reads allowed only as granted; management requests rejected by server. |

## 16. Data Intelligence relationships

| ID | Steps | Expected result |
| --- | --- | --- |
| REL-01 | Build relationships from the current test snapshots and inspect progress/errors. | Current owned graph or explicit failure; retry does not fabricate a graph. |
| REL-02 | Explore map/list/connection/dataset/field filters, selection and details. | Correct containment, keys, descriptions and selection; large-graph limits are disclosed. |
| REL-03 | Compare declared foreign keys against database constraints, including composite-key fixture order. | Actual declared targets/order or a coverage warning, never an invented target. |
| REL-04 | Inspect cross-source proposals and their evidence/status. | Proposed matching identifiers are not presented as proven joins or execution authority. |
| REL-05 | Accept, reject and reset a proposal on cloned fixtures. | Exact decision/revision persists; no source-database mutation. |
| REL-06 | Add/edit dataset and field descriptions; test empty and >1000-character values. | Supported application annotation persists; limit validation is clear. |
| REL-07 | Rebuild unchanged evidence, then change relevant test metadata and rebuild. | Review persists only for unchanged fingerprints; changed evidence needs review. |
| REL-08 | Edit a stale graph revision in a second tab and disconnect a fixture source. | Stale edit rejected; disconnected nodes cannot authorize current queries. |

## 17. Data Intelligence questions, exact results and execution strategy

Before testing, verify counts using read-only SQL on your test copy:

```sql
SELECT 'regions' AS dataset, COUNT(*) AS rows FROM northwind.regions
UNION ALL SELECT 'shippers', COUNT(*) FROM northwind.shippers
UNION ALL SELECT 'suppliers', COUNT(*) FROM northwind.suppliers
UNION ALL SELECT 'territories', COUNT(*) FROM northwind.territories
UNION ALL SELECT 'products', COUNT(*) FROM northwind.products
UNION ALL SELECT 'orders', COUNT(*) FROM northwind.orders
UNION ALL SELECT 'order_details', COUNT(*) FROM northwind.order_details;
```

With the unchanged original data: regions 4; shippers 3; suppliers 29;
territories 53; products 77; orders 830; order_details 2155. These are fixture
expectations, not assertions that every edited database must retain those totals.

| ID | Steps | Expected result |
| --- | --- | --- |
| QUERY-01 | Ask “Count all rows in PostgreSQL northwind.orders”; create a plan but do not run. | Metadata-only reviewed plan; count result appears only after execution. |
| QUERY-02 | Review source, fields, joins, filters, grouping, metrics, sorting, output limit and physical strategy. | Plan matches the question or requires correction/clarification before Run. |
| QUERY-03 | Run the orders count; repeat for products and order_details. | Exact unchanged-fixture results 830, 77 and 2155. |
| QUERY-04 | Query selected product names/prices; filter, sort and set a small output limit. | Correct rows/order/limit compared independently with SQL; limit is not mistaken for total input coverage. |
| QUERY-05 | Query SUM/AVG/MIN/MAX/COUNT and grouped aggregates, including NULL/zero/negative fixtures. | Exact supported arithmetic/null behavior; no rounding/truncation hidden as complete results. |
| QUERY-06 | Check order 10248 discounted line-item sales using order_details.unitPrice × quantity × (1-discount), excluding freight. | With the supplied seed, total is 440.00; use historical detail price, not current product price. |
| QUERY-07 | Run a supported same-PostgreSQL join/aggregate and a supported Mongo aggregate; inspect execution evidence. | Actual strategy/source counts/snapshot evidence; no claim that every plan pushes down. |
| QUERY-08 | Run the federated category query below after reviewing the products→Mongo categories edge. | Eight groups/2155 matched fact rows on the unchanged fixture; sums/averages match independent checks. |
| QUERY-09 | Inspect federated fragment evidence, transferred records/bytes and read windows. | Normally three fragments and 24 transferred records for that reviewed fixture plan; no atomic cross-database snapshot claim. |
| QUERY-10 | Ask an ambiguous/unknown-field question or request an unsupported write/delete. | Clarification/safe rejection; no invented field, mutation or business fact. |
| QUERY-11 | Execute a supported bounded fallback plan and an input/transfer/group/output-limit overflow fixture. | Correct complete fallback result or explicit refusal; never partial totals labeled complete. |
| QUERY-12 | Test null/missing/duplicate target keys and unmatched join keys in cloned fixtures. | Strict join failure rather than silently dropped or multiplied facts, including when a later filter could hide them. |
| QUERY-13 | Change reviewed metadata or let a saved plan expire before execution. | Stale/expired plan rejected; create a fresh reviewed plan. |
| QUERY-14 | Test high precision, unsafe-JS integers and supported/unsupported arithmetic, including division fixtures. | Safe decimal/integer serialization or bounded fallback/refusal; no precision loss claim. |

Federated question:

```text
For ALL PostgreSQL northwind order_details rows, calculate discounted line-item
sales as unitPrice * quantity * (1 - discount), excluding freight. Join products
by productID, then MongoDB categories using the accepted products categoryID
relationship. Group by MongoDB categoryName. Return SUM and AVG of that line-item
expression. Sort by SUM descending. No date filter.
```

Independently check its PostgreSQL portion with:

```sql
SELECT p."categoryID", COUNT(*) AS line_count,
       SUM(od."unitPrice"::numeric * od."quantity" *
           (1 - od."discount"::numeric)) AS sales,
       AVG(od."unitPrice"::numeric * od."quantity" *
           (1 - od."discount"::numeric)) AS average_line_sales
FROM northwind.order_details od
JOIN northwind.products p ON p."productID" = od."productID"
GROUP BY p."categoryID"
ORDER BY sales DESC;
```

Use the actual Mongo categoryID/categoryName mapping to check labels. Compare
decimals numerically, not by trailing zeros. If discount is a floating-point
column, distinguish its stored binary representation from intended decimal
values before diagnosing tiny precision differences.

## 18. Durable query jobs, cancellation and expiry

| ID | Steps | Expected result |
| --- | --- | --- |
| JOB-01 | Run a fresh reviewed query and observe job ID/stage/elapsed time/attempt/progress. | Durable owned job; only measured counts/stages, no invented percentage. |
| JOB-02 | Refresh during a running federated job; reopen Questions. | Same job resumes observation; no resubmission or lost completed result. |
| JOB-03 | Navigate away/back; open Recent query jobs and select an existing completed job. | Exact retained job/result loads without reexecution. |
| JOB-04 | Cancel queued and active jobs in staging. | Queued cancellation avoids reads; active job reaches stopping/cancelled with no partial result. |
| JOB-05 | Race cancel versus completion repeatedly. | Whichever terminal publication/cancel wins is respected; success may legitimately win the race. |
| JOB-06 | Wait 15 minutes after success; keep result open and try reopening after expiry. | Result rows disappear/become unavailable; succeeded metadata remains until its retention expires. |
| JOB-07 | Inspect retained metadata after the 24-hour retention/cleanup window in staging. | Maintenance removes eligible terminal metadata; do not claim deletion while the service is stopped. |
| JOB-08 | Simulate lost submit/status responses; explicitly retry unchanged request. | Same admission key recovers one job; status retry does not create a new execution. |
| JOB-09 | Restart only staging API during a job; then separately test worker interruption. | Durable state survives API restart; eligible interrupted work recovers once with a fresh fenced attempt. |
| JOB-10 | Test repeated interruption, absolute timeout, unavailable source and failed database statement. | Bounded failure with no partial totals; ordinary source failure is not silently retried as recovery. |
| JOB-11 | Submit to configured owner/workspace/global admission and result-capacity limits using a controlled fixture. | Explicit bounded rejection; at most configured active claims and per-owner limit. |
| JOB-12 | Try another owner/workspace/job ID; revoke permission or alter graph before retrieval/publication. | No unauthorized result/progress access; current authority/freshness checked. |

Default configured job budget is 180 seconds from submission (operator may set
45–300), constrained by plan expiry; result TTL is 15 minutes and terminal metadata
retention is 24 hours. Verify the deployment's advertised settings. Full lease,
encryption, fencing and publication races require integration tests; manual UI
observation alone cannot prove those internals.

## 19. Monitoring, security and accessibility

| ID | Steps | Expected result |
| --- | --- | --- |
| OPS-01 | Compare Monitoring run counters and latest records to known QA runs; exercise Refresh. | Correct workspace counts/evidence, not copied client demo values. |
| OPS-02 | Inspect trigger provider/type/source/schedule/timezone, preparation, baseline, last poll and failure state. | Preparation, connectivity and successful polling remain distinct. |
| OPS-03 | Page through trigger/policy evidence and inspect worker health with authorized access. | Bounded complete pages; component heartbeat/backlog/active-run observations are truthful. |
| OPS-04 | Exercise unauthenticated, viewer, builder, approver/admin and second-workspace API requests in staging. | Server enforces each operation and workspace ownership, regardless of visible controls. |
| OPS-05 | Test untrusted Origin/CSRF-sensitive requests and tampered workflow/revision/job IDs with fixtures. | Rejected; opaque identifiers do not grant authority. |
| OPS-06 | Scan safe fixture responses, UI feedback and redacted logs for secret/stack leakage. | No credentials/tokens/connection URI/raw provider exception disclosure. |
| OPS-07 | Tab/Shift+Tab through each screen/dialog; Escape/Enter; inspect focused field errors. | Labels, focus, disabled state, dialog focus return and accessible validation work. |
| OPS-08 | Test touch targets, long content, tables, portrait/landscape and visible phone keyboard. | Controls remain reachable; tables can scroll locally without page-wide overflow. |
| OPS-09 | Repeat the smoke path on the actual iPhone/iOS 27.0.1, desktop Chrome and Safari, and Android Chrome if supported. | Content loads and interactions work; desktop mobile emulation is not physical-device proof. |
| OPS-10 | Background/lock the phone during a read/job, resume, and switch Wi-Fi/mobile data. | Reconnection updates confirmed state or displays a recoverable error; no duplicate action. |

## 20. Failure recovery and sustained operation — staging only

Agree service targets before judging performance. The numbers below are proposed
acceptance targets, not measurements or configured promises: content visible in
5 seconds on a normal connection; list/detail API p95 below 2 seconds at agreed
load; zero duplicate writes/data-loss incidents; zero critical permission bypasses.
Generation and query jobs have separate bounded workloads and must not inherit
the ordinary page/API response target.

| ID | Steps | Expected result |
| --- | --- | --- |
| STABLE-01 | Open 5, then 10 concurrent test sessions through a small navigation/read workload; record CPU/RAM/API timings/backlog. | Meets agreed targets without corruption; these loads do not establish maximum supported capacity. |
| STABLE-02 | Gradually increase staging load to the actual required concurrency and documented data sizes. | Bounded resource use/backpressure; failure threshold is measured, not assumed. |
| STABLE-03 | Run a 2-hour smoke/read/job loop; after fixes, repeat for 24 hours. | No unexplained memory growth, stuck loading/jobs, duplicated effects or persistent failures. |
| STABLE-04 | Interrupt browser networking and simulate bounded 502/503/504 responses. | Confirmed data/input survives; bounded allowed reads retry; uncertain writes are not blindly replayed. |
| STABLE-05 | Restart staging frontend, API and worker separately, then reboot the test host. | Services recover under supervision; persisted drafts/revisions/runs/jobs remain consistent. |
| STABLE-06 | Interrupt a worker after a test provider accepted an effect but before confirmation. | Unknown effect requires reconciliation; no automatic duplicate email/Sheet/calendar write. |
| STABLE-07 | Inject DB unavailability, exhausted storage and provider timeout/rate-limit failures safely. | Actionable bounded failures/backpressure; no false success or partial authoritative result. |
| STABLE-08 | Restore backups into a new isolated environment with matching encryption keys. | Revisions, audit, idempotency, connections and encrypted result handling verified; not merely a successful file copy. |
| STABLE-09 | Stage a new frontend build with previous static dependencies retained, then exercise old/open and fresh tabs. | Both hydrate; no JS/CSS chunk 404s. Use the asset-retention utility before activation. |
| STABLE-10 | Exercise planned rollback before new writes and separately reconcile a fixture after new writes. | No stale database rollback that loses accepted writes/effect evidence. |
| STABLE-11 | Review SQLite/auxiliary DB growth, retained jobs/results, disk and WAL/log size after the soak. | Retention works at its actual maintenance cadence; growth remains within agreed capacity. |
| STABLE-12 | Verify unauthorized/disabled automation remains blocked throughout failure/recovery tests. | Recovery never bypasses current grants, approval gates or disabled releases. |

## 21. Automated release checks

Run these in a verified isolated checkout/build directory with the repository's
installed dependencies. Do not overwrite the running production `.next` while
checking a build. Use Node 22 as in the existing verified setup. Commands below
are instructions, **not fresh passing results from preparing this guide**.

```bash
# From an isolated copy of the repository with its Python integration environment
.venv-integrations/bin/python scripts/validate_contracts.py
.venv-integrations/bin/python scripts/generate_ui_contracts.py --check
.venv-integrations/bin/python -m pytest -q tests connector_extension/tests

cd frontend
npm run typecheck
npm run lint
npm run test
npm run build
npm run test:e2e
```

The broad backend run needs installed integration dependencies and
`BUILDER_TEST_POSTGRES_DSN` privately configured for a disposable nonadministrative
test database. A skipped dependency is not passing coverage. Inspect each failure;
historical suite pass counts do not certify the current tree.

Default Playwright config starts an offline test API on 8011 and frontend on 3100,
uses a fresh test DB and disables real connectors. Run against an isolated build
using `BUILDER_E2E_FRONTEND_DIR` and a dedicated
`BUILDER_E2E_DATABASE_DIR` as documented in `../phase7-release-verification.md`.
The data-query fixture suites also have their explicit isolated-build config:

```bash
QUERIES_FRONTEND_DIR=/ABSOLUTE/ISOLATED/frontend \
  npm run test:e2e -- --config playwright.queries.config.ts
```

Offline fixtures prove application behavior for the exercised cases; they do not
prove real Google consent, model correctness, inbox delivery or live cloud
availability. Run the controlled provider acceptance cases separately. The current
source-control inventory supplements these suites; it is not generated proof
that every listed control has an automated test.

## 22. What continuous stability requires

Manual testing catches defects; it cannot promise availability at all times.
This guide does not install monitoring, alerts, backups, CI, failover or a new
production identity system. Qualify and operate them explicitly:

One source discrepancy already needs an acceptance check: Monitoring displays
“every 15 seconds”, but `LiveRuntimePanel` currently schedules its next read
5 seconds after completion. Its loop is serialized, but the displayed interval
and implementation disagree. Record this under OPS-02/your defect ledger; this
documentation task does not change the polling code or certify its live timing.

| Cadence | Required check | Failure response |
| --- | --- | --- |
| Every release | Type/lint/contracts/unit/integration/browser gates; current changed-control coverage; physical-mobile smoke; retained-asset check | Block rollout for relevant failures; keep the last verified artifact. |
| Every 1–5 minutes (proposed) | HTTPS reachability plus browser smoke that waits for real Overview content; authorized API and worker readiness | Alert the responsible operator; a 200 HTML response alone misses the skeleton defect. |
| Every 1–5 minutes (proposed) | Error rate, API p95, worker heartbeat age, queue age, active jobs, restart count, CPU/RAM/disk/DB growth | Alert against agreed thresholds; investigate before uncontrolled restart/replay. |
| Daily | One controlled read-only workflow/data query; backup freshness; failed/unknown effects; retention and provider auth health | Reconcile failures; do not resend uncertain external effects. |
| Weekly | Critical device/browser smoke, role/access regression, restore drill sample and capacity trend review | Track failures to owners and retest fixes. |
| Before expanding usage | Individual application login/workspace isolation, realistic capacity qualification, recovery objectives, dependency/failover design | Do not claim production readiness from a shared demo identity or test counts. |

Suggested initial service objective for discussion: 99.9% successful eligible
requests per month, measured externally, with an explicit latency target and error
budget. It is not currently verified by this guide and does not mean zero downtime.
Choose an agreed RPO (acceptable data loss) and RTO (recovery time); prove them by
timed restoration tests. Preserve encryption keys and effect/idempotency records.

For read-only service status on this host:

```bash
systemctl is-active agentic-builder-frontend.service \
  agentic-builder-backend.service agentic-builder-worker.service
```

Active processes alone do not establish functional health. Use an authorized
`/api/backend/worker-health` read for the existing worker-health endpoint and a
browser content check. Treat reported provider heartbeat/readiness as observation,
not proof that a provider action will succeed. Never put privileged cookies or
tokens into public monitoring URLs.

## 23. Acceptance and release decision

1. Complete every relevant row and expand every visible dynamic option/control.
2. Require zero unresolved critical/high defects: data loss, unauthorized access,
   duplicate external effects, false results, stuck essential paths or exposed secrets.
3. Record optional missing configuration as BLOCKED and explicitly exclude it from
   release scope; do not silently count it as PASS.
4. Attach current automated results, browser/device evidence and independent data
   comparisons. Separate offline fixtures from live-provider results.
5. Pass the agreed soak/load/restore/release tests and confirm alert delivery to
   the responsible operator. Fix and rerun relevant cases after any code/config change.
6. Keep known limits visible: draft-only governance/agent controls, unsupported
   knowledge ingestion/simulation, shared demo identity, independent cross-DB
   snapshots, bounded query inputs, expiring results and nontransactional external
   multi-service writes. A feature limit must not be disguised as an implemented feature.

No manual plan can prove every possible execution path. Coverage here means every
identified screen/feature/control owner has an explicit test path and result, with
additional automation for concurrency, authorization, exact arithmetic and recovery.
