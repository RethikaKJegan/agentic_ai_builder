# Google tools — Phase 2

Phase 1 OAuth routes, encrypted connection records and account management UI remain unchanged. Phase 2 adds an explicit `metadata.google_connection_id` reference to immutable workflow revisions. Workflows without that field retain their existing server credentials.

## UI: select the account before generation

1. Open `/app` and choose the account in **Google account** above the process prompt.
2. Generate the workflow. Sheets discovery uses that connection, and the server stamps its reference into the returned draft. Identical prompts with different selected accounts receive different planned workflow IDs.
3. Review, save, validate, approve and publish through the existing controls. Existing policy gates are retained.
4. To change the account on an existing workflow, open **Workflow details → Google connection for this revision**. Choose an account and click **Save account binding**. This saves a new draft revision and retains other current edits. Review/publish it normally; existing runs and projects retain the original revision connection.

There is no implicit default-account substitution. An unavailable, disconnected, unauthorized or insufficiently scoped selected connection fails explicitly.

## UI: check tools without a model-generated plan

Open `/app/integrations` → **Test Google tools with a workflow**.

1. Select a connected account.
2. Choose an enabled registered operation.
3. Replace sample input placeholders with your exact test resource, recipient or event ID. Samples are editable examples, not execution defaults. For Calendar, set a future date, timezone-aware start/end and explicit timezone.
4. Click **Create tool-check draft**. This saves only a draft; it sends no email and makes no Google write.
5. In the editor, validate, submit/approve, publish and activate as required by the existing lifecycle. Start the manual workflow from Workflows using its existing Run control. Write steps pause at their configured approval gate; approve the exact test action in Approvals.
6. Inspect Execution and the actual Google resource. Node trace includes **Google account used**, operation results and provider identifiers. API acceptance of email is not confirmation of inbox delivery.

Supported checks reuse registered Sheets read/discovery/create/add-tabs/upsert, Gmail search/message/thread/draft/send/reply, and Calendar list/create/update/cancel tools. Only operations installed/enabled in this deployment are listed. Attachment retrieval stays available through supported workflow tools and its artifact handling; no separate attachment-upload UI was added.

For `google_sheets_upsert_record`, provide reviewed write targets matching the actual Sheet headers, for example:

```json
[{"spreadsheet_id":"YOUR_ID","range":"Checks!A1:B100","identity_column":"id","writable_columns":["status"],"allow_create":true}]
```

Matching operation inputs:

```json
{"spreadsheet_id":"YOUR_ID","range":"Checks!A1:B100","identity":"check-1","fields":{"status":"Checked"}}
```

Operator resource/recipient ceilings still apply. A connection grants account access; it does not override reviewed destinations or an operator allowlist. Gmail replies require access to read the original message and permission to send. Calendar list discovery of all calendars is not enabled by the Phase 1 event-only scopes; use `primary` or an explicitly permitted calendar ID.

## Manual acceptance sequence

- Account A: read a Sheet shared with A and inspect returned rows/account provenance.
- Use the upsert example to write a test record; check the exact row in Google Sheets.
- Create a draft, then explicitly send to an allowed test inbox; inspect Drafts/Sent and the recipient inbox.
- Read/reply to an actual message using its Gmail API message ID, not an RFC Message-ID or browser URL.
- Create a future primary-calendar event, update the returned event ID, then cancel that same test event. Calendar operations use `sendUpdates=none`; invitations are not automatically sent.
- Account B: repeat with a different accessible Sheet and verify that the account really changes. An inaccessible Sheet should fail; it must not fall back to A.
- Missing scope: select a connection lacking the required service permission. The action must report `GOOGLE_SCOPE_REQUIRED`; grant access through unchanged Phase 1 Manage access.
- Disconnect the selected connection. New operations stop with reconnection required. Legacy workflows without a selected connection remain unchanged.
- For a new procurement project, select the connection before generation. All newly created child action workflows inherit the original owner revision's connection, including RFQs, quotation reads, award/PO sends, fulfilment messages, tracking writes and Calendar operations. Do not repoint an existing project to another account.
- Keep the worker running for background processing. Restarting API/worker preserves the stored binding; closing the browser does not change it.

## Implementation

`workflow_api/google_tools.py` resolves owned, scoped credentials through the existing Phase 1 service and clones adapters per invocation. It never modifies a global Google client/account. `runtime/graph.py` applies it after normal workflow/run binding and records safe account provenance in existing node.started events. Standard Sheets adapters accept a backend-only credential supplier; extension Gmail/Calendar/Sheets clients reuse their existing scopes, schemas, recipient restrictions, resource checks and effect journals. Existing SMTP-shaped actions with a selected connection use Gmail API after their existing approval/recipient checks and retain their accepted output schema.

`IntegratedProcurement.run_action` copies the connection from the exact immutable owner revision into child drafts. Provider trigger polling uses the same authorized revision binding. Drive/Docs operations with an explicit selected connection fail as unsupported instead of using another account; those services require a later scope/connector phase.

The API `POST /integrations/google/tool-check-draft` accepts a selected connection ID, allowlisted installed tool ID, explicit inputs and optional Sheet targets. It invokes the normal save_workflow_version operation; it does not bypass execution, approvals or resource restrictions. Shared workflow/agent/tool schemas remain unchanged; the additive metadata shape is documented in `shared/contracts/integrations/google-workflow-binding-v1.schema.json`.

## Deployment boundary

The current deployment still uses a shared demo authenticated subject. Use test accounts until individual application login and workspace membership are implemented. Google OAuth connection management does not itself provide isolation between visitors sharing that subject. Real provider/manual acceptance is distinct from automated mocked-provider checks.

## Verification and rollout

Deployed October 17, 2026. API, frontend and worker are active. Public desktop/mobile checks verified the generation selector, revision selector, registered-operation draft form, and absence of document horizontal overflow/browser errors. Phase 1's account-management routines and Google OAuth configuration were not changed.

Fifteen selected-account backend tests passed, including a complete fake-provider procurement run through four RFQ sends. Thirteen final Phase 1/legacy procurement regression tests passed. Frontend types, lint, 33 focused tests and production build passed. Live provider writes have not been run automatically; use the manual sequence above with your own test resources. Production per-person login remains outside this phase.
