# Optional connector extension

This package adds connector capabilities using new files only. It does not alter the existing Builder launcher, frontend source, published workflows, database, `.env`, `credentials.json` or `token.json`. It is not activated by importing `connector_extension` or by starting the original application.

The extension uses the accepted Registry, workflow service, graph runner, approvals and trace contracts. Its separate transport avoids importing `workflow_api.main.app`, whose module-level initializer creates the original application's database. Its default state directory is `.local/connector-extension/`, and its default loopback API port is **8003**.

## Operations

| Tool ID | Capability | Behavior |
| --- | --- | --- |
| `google_sheets_read_rows` | `read_spreadsheet` | Read a bounded table from any supplied spreadsheet link accessible to the connected account |
| `extension_sheets_discover` | `discover_spreadsheet` | Discover actual tab titles, headers and bounded ranges from a spreadsheet link |
| `google_sheets_upsert_record` | `update_spreadsheet` | Create/update a stable-ID record in approved columns of an approved table |
| `extension_sheets_create` | `create_spreadsheet` | Opt-in creation of a new spreadsheet with reviewed tabs and literal headers |
| `extension_sheets_add_tabs` | `create_spreadsheet_tabs` | Opt-in creation of missing tabs; compatible existing tabs are reused without editing their rows |
| `extension_calendar_discover` | `calendar_discover` | Discover connected calendars, names, timezones and access roles |
| `extension_calendar_list` | `calendar_list` | List events in a workflow-selected calendar with time filters and pagination |
| `extension_calendar_create` | `calendar_create` | Create a timed or all-day event with optional reminders |
| `extension_calendar_update` | `calendar_update` | Update an event's summary, description, time and reminders |
| `extension_calendar_cancel` | `calendar_cancel` | Delete/cancel an exact event |
| `extension_mail_profile` | `mail_profile` | Discover the authenticated account identity without a preset sender |
| `extension_mail_search` | `mail_search` | Search the authorized Gmail mailbox with workflow-selected queries and pagination |
| `extension_mail_message` | `mail_message` | Read a message's headers, plain-text body and attachment metadata |
| `extension_mail_thread` | `mail_thread` | Read up to 100 messages in a Gmail thread |
| `extension_mail_attachment` | `mail_attachment` | Retrieve a message attachment into a private workflow-scoped artifact |
| `extension_mail_draft` | `mail_draft` | Create a draft, optionally with attachments; does not send it |
| `extension_mail_send` | `mail_send` | Send a message, optionally with attachments |
| `extension_mail_reply` | `mail_reply` | Reply using the original thread, subject, sender/Reply-To and MIME references |
| `extension_web_search` | `web_search` | Optional Brave search with workflow-selected topics, country, language, freshness and page |

Use one Sheets call per table and combine results through the existing agents. Separate spreadsheet IDs are supported. The opt-in procurement coordinator now supports mapped table-to-BOQ extraction and section/vendor RFQ grouping. Free-text/document extraction, quotation comparison, award/PO automation and fulfilment orchestration remain future workflow work. Calendar reminders notify through Calendar; this package does not implement an overdue-order worker. Mail reads are explicit tool operations; the existing customer IMAP monitoring process is not changed or started here. PDF/DOCX/OCR and quotation-attachment parsing are not included. Spreadsheet/tab creation is separately opt-in; see [spreadsheet provisioning](procurement/SPREADSHEETS.md). Calendar guest invitations and unrestricted recipient discovery are not included.

The new adapters reuse existing spreadsheet ID normalization, bounded table parsing, reviewed write-target validation and record locks. They send provider requests through the extension's bounded HTTP transport. Sheet writes use RAW cell values, so strings beginning with `=` remain literal text.

## Separate setup

Run all commands from `/home/raf/agentic-ai-builder`. Use the existing `.venv-integrations` environment; no dependency installation or lockfile change is required. Its existing runtime and Google integration dependencies are reused.

Start with all providers disabled:

```sh
mkdir -p .local/connector-extension
cp connector_extension/config.example.json .local/connector-extension/config.json
.venv-integrations/bin/python -m connector_extension --config .local/connector-extension/config.json --port 8003
```

The sample configuration starts with **`enabled_providers: []`** and requires no resource IDs, ranges, sender or recipient presets. Select only the required providers from `google_sheets`, `google_calendar`, `gmail`, `brave_search`. Nothing creates a workflow or calls a provider on startup. Tools without their required connection remain unavailable. Sheets read, write and discovery become available with the Google connection; specific write destinations are reviewed per workflow.

**Sheets are generalized by default.** Authorize your Google account once, then paste any accessible spreadsheet link into a workflow setup prompt or supply it to a read/discovery tool at execution time. Different workflows can use different spreadsheets without editing the connection configuration. The sample configuration contains no spreadsheet IDs or ranges.

For example, enter a prompt such as: “Read [spreadsheet link], discover its tabs and headers, and summarize the requirements.” Setup discovery inspects only the links you supply, returning actual tab titles, header names and bounded table ranges before generation. It does not send business rows to the planner. Agents select the relevant discovered table; ambiguous tab/identity choices should remain unresolved for clarification. Generation still requires the optional model setup described below. You can also invoke `extension_sheets_discover` through a canonical read-only workflow without a model.

Read/discovery inputs accept `spreadsheet_url` or the compatible `spreadsheet_id` field (which also accepts a URL). Supply exactly one. The read tool uses an explicit bounded range chosen from discovery, such as `Requirements!A1:F1000`. Discovery returns at most 50 tables, caps its selected range to 100,000 cells and its header previews to 200 columns, and exposes `has_more` when more tables exist. It never creates tabs or guesses headers. Google account permissions still determine which spreadsheets are accessible.

For edits, describe the destination link, tab, stable identity and desired columns in the setup prompt. Each workflow declares reviewed `metadata.sheet_write_targets`; the connector binds to those exact destinations and columns before a write. Spreadsheet IDs are extracted internally from links. The existing write input field is called `spreadsheet_id`, but accepts a URL as well as a bare ID. Existing tabs, unique headers and Google write consent remain required. General access does not let incoming rows/tool results create write grants.

Optional `sheet_reads` and `sheet_writes` arrays are additional operator restrictions. Omit them or leave them empty for generalized access. **If you copied the earlier sample config with placeholder/fixed spreadsheet lists, remove those two arrays** to enable the generalized default. Nonempty lists intentionally continue restricting access. Unbound writers without reviewed workflow targets deny writes; they do not gain all-account write access merely because the configuration is empty.

**Calendar is generalized.** Discover calendars available to the connected account with `extension_calendar_discover`, then select a calendar in the workflow; no Calendar ID needs to be placed in server configuration. Omitting `calendar_id` uses that account's primary calendar. Planning prompts mentioning calendars, meetings, reminders or deadlines receive a read-only catalog of actual calendars/names/timezones/access roles; ambiguous named choices should remain unresolved. Discovery is paginated and does not return event contents. Google enforces read/edit permissions for each selected calendar.

Events accept either start/end dates (end is exclusive) or offset-aware `dateTime` values plus IANA `timeZone`. An event update supplies a complete event summary/start/end; it is not an arbitrary Calendar API patch. Reminder overrides use `email` or `popup` and minutes before the event. Calendar guest invitations are omitted; API requests specify `sendUpdates=none`. A nonempty optional `calendars` array remains an additional operator restriction; omit it or leave it empty for general account access.

**Mail is generalized.** Connect a Gmail account once. Without `mail_account`, the sender is discovered from that authenticated account's profile when a draft/send/reply executes; `extension_mail_profile` also exposes its identity as a read tool. Gmail endpoints use `users/me`, so the account selected during OAuth determines the mailbox. A server sender address or list of vendor/customer recipients is not required.

Each draft/send takes its recipient, subject, body and attachment references from the workflow inputs or reviewed source records. Replies use the selected original message's actual Reply-To/From and thread references. One recipient is accepted per action; multiple vendors/customers use separate workflow actions. Exact run approval is still required before provider mutation. Search queries, message IDs, thread IDs and attachment references are selected per workflow. Business-specific RFQ/case correlation remains workflow logic. A nonempty optional `mail_recipients` list restricts destinations; an optional `mail_account` preserves the legacy explicit sender override, which Gmail must permit. Omit these settings for the generalized defaults.

If using an earlier extension config, remove `calendars`, `mail_account` and `mail_recipients` along with old Sheet restrictions to use account/workflow-selected resources. Explicit nonempty lists continue applying their restrictions; they are never silently ignored.

## Independent Google consent

Enable the corresponding Google APIs in your Google project. The helper reads the selected client JSON but writes only a new extension token. It requests only scopes for the provider groups you select. Original OAuth files are never overwritten.

```sh
.venv-integrations/bin/python -m connector_extension.authorize_google \
  --client credentials.json --providers google_sheets google_calendar gmail
```

This starts a local browser callback on port **8766**, separate from the existing helper. For a remote VM, add `--no-browser` and use an appropriate SSH tunnel/browser access to that callback; the extension helper does not implement the original pasted-redirect/Playground modes. A web OAuth client must allow its callback URI. If verification fails, the previous extension token is preserved. Token scope changes require running this separate helper again; editing configuration is not consent. Calendar discovery additionally needs `calendar.calendarlist.readonly`; if your extension token predates this discovery tool, rerun the helper for `google_calendar` once to grant that permission.

The extension token is stored privately at `.local/connector-extension/google-token.json`. Google Sheets writes need spreadsheet edit consent and account access to the target. Calendar writes need event-edit consent. Gmail reads, draft creation and sends require their selected scopes. The helper verifies offline refresh access and returned scopes before saving. Google still enforces actual resource permissions on every request.

## Optional search and models

Brave search is disabled unless selected in `enabled_providers` and an extension-only API key is supplied through **`BUILDER_EXTENSION_BRAVE_API_KEY`**. Enter that key privately in your shell/secret manager; do not put it in a workflow or the committed example config. Set `search_cost_per_call_usd` to your plan's applicable per-request cost; zero is an operator setting, not a claim that Brave is free. Search takes any bounded query and optional `country`, `language`, `freshness` (`pd`, `pw`, `pm`, `py` or an ordered date range), and `page` (0–9) from workflow inputs. It returns source URLs/snippets and pagination evidence when the provider supplies it. No topic, vendor or business domain is fixed in configuration. Search never fetches returned pages or treats snippets as instructions. Review sources before using them as evidence; supplied vendor lists remain the authority for recipient selection.

Manual connector workflows need no model. Optional natural-language generation uses the configured `OPENAI_API_KEY` and `OPENAI_MODEL` through the existing planner, with the extension's enabled catalog/resource context. Optional model execution also needs `BUILDER_EXTENSION_MODEL_RATES` (exact model ID to `input_per_token`/`output_per_token` mapping) and, if required, `BUILDER_EXTENSION_MODEL_TOKENIZER`. No rate/model defaults or credentials are invented. The connector catalog alone does not guarantee a model generates a correct procurement workflow.

## Using the existing UI without changing its files

The connector backend is independent. Start an isolated copy of the existing frontend with the included helper:

```sh
.venv-integrations/bin/python -m connector_extension.launch_ui --port 3002 --api-port 8003
```

This copies the current frontend source into a new extension-owned directory, shares the already-installed dependency directory, builds only the copy, and starts it on port 3002 with an explicit `BUILDER_API_URL`. The original frontend build/source and running process stay untouched. Open `http://127.0.0.1:3002` for new extension workflows. Browser storage is separate by origin/port, and the extension uses its own HttpOnly `builder_extension_session` cookie, preserving the original session even in the same browser. If using a non-default UI port, add its exact origin to `BUILDER_EXTENSION_UI_ORIGINS` for the backend.

The existing UI discovers tool definitions through `/tools`. Its editor remains unchanged and may need canonical input configuration for the new operations. The frontend's pre-existing identical-run retry-key reuse and publication recovery limitations remain unchanged. Supply a fresh execution key for each new intentional API run; retain that key for retries of that run. This package does not fix unrelated UI defects.

## Canonical smoke workflow and execution

`connector_extension.examples.connector_workflow` builds a single-tool draft compatible with the existing workflow contract. It is an example builder, not an automatic provider action:

```python
from connector_extension.examples import connector_workflow
workflow = connector_workflow(
    'google_sheets_read_rows',
    {'spreadsheet_url': 'https://docs.google.com/spreadsheets/d/YOUR_ID/edit', 'range': 'Requirements!A1:F1000'},
    workflow_id='requirements_connector_check',
)
```

Save it using `save_workflow_version`, validate it, approve/publish the exact revision, then execute it through the existing canonical envelopes. The new API exposes the same workflow, tool, run, approval, overview and monitoring routes used by the frontend. Existing Registry validation owns assignments. The example automatically includes a run approval gate for any write operation. Runtime traces contain actual tool observations/results/handoffs. Review the configured tool inputs before approving writes; this extension does not alter the legacy SMTP-only email-preview UI. No demo workflow is seeded into either database.

Get exact tool schemas without creating state or starting providers:

```sh
.venv-integrations/bin/python -m connector_extension --catalog
```

## Attachments

Message/thread attachment metadata uses a stable `part_` MIME-part reference when Google supplies its immutable part ID. Download resolves that reference within the exact selected message and uses the current opaque Google attachment ID, which can change between reads. Matching legacy provider IDs are also accepted, bounded to 4096 URL-safe characters. Downloads return `{artifact_id, filename, mime_type, size}` rather than raw base64 or local filesystem paths. Pass `{artifact_id, filename, mime_type}` in the `attachments` array of a draft/send/reply. Each attachment and the combined outgoing attachments are bounded to **five MiB**. Only plain-text message bodies are exposed; HTML-only bodies remain empty, with the provider snippet available. Attachments are not interpreted or executed.

To stage an operator-selected local document for a new workflow:

```sh
.venv-integrations/bin/python -m connector_extension.artifacts \
  --file /path/to/approved-document.pdf --workflow-id your_workflow --version 1
```

The printed opaque reference belongs only to that exact workspace/workflow/revision. Download or stage attachments again when moving to a new revision. Artifacts use immutable hashes and private file permissions; connector inputs cannot select arbitrary local paths.

## Action approvals and recovery

Reviewing another extension workflow retains existing workflows’ exact unexpired tool approvals. The original approval-snapshot operation still supports replacement and explicit revocation.

All provider writes, including draft creation, require Registry publication review and a dedicated approval gate immediately before the explicit tool node. The extension rejects model-selected writes lacking such a concrete reviewed action; dynamic specialists may use read tools. The extension provides no direct-send flag. A committed extension effect journal records the intent before each provider mutation and retains successful responses for same-effect retries. An unknown write result is never automatically replayed. Gmail Message-ID is correlation data, not a delivery guarantee. Calendar create IDs are derived from the action reference. A new run ID still identifies a new action for existing operations; the extension does not deduplicate arbitrary repeated business orders across runs. The new spreadsheet setup tools instead deduplicate by workspace, tool, project and stable creation key, with exact normalized inputs.

After an uncertain result, inspect the provider using read tools and reconcile the action before deliberately starting another one. Do not erase journal entries to trigger a resend. Local Sheet locks coordinate only this extension's state directory; they do not coordinate other applications or separate extension installations. External Sheet edits can race a read/write; no distributed transaction or provider compare-and-swap is claimed.

Report exports (`extension_sheets_create_report`) use the bound workflow namespace
and runtime action reference (`run_id:node_id`) as well as project/creation key.
Each fresh run creates a separate approved report. Retrying the same action with
identical content reuses its verified receipt; changed content under that action
still fails before mutation. Permanent spreadsheet setup retains its original
project-level identity. To reconcile a new report, pass the original action
reference as `effect_id` to `ReportSheetsSetup.reconcile`; omitting it addresses
legacy report receipts. Existing journal entries and spreadsheets are preserved.

Default state is separate: workflow history, effect intents, artifacts, credential refresh and Sheet locks remain under `.local/connector-extension`. `--state-dir` may choose only a subdirectory there. Permissions/grants are reconstructed by the existing Registry on restart. The launcher starts a runtime worker for manual runs and approval expiry; it does not start existing customer reply/source polling. When procurement is explicitly enabled, a separate bounded coordinator advances only registered first-slice projects after actual runtime results and human gates. It does not add quotation polling or scheduled order reminders.

## Verification

```sh
.venv-integrations/bin/python -m unittest discover -s connector_extension/tests -v
.venv-integrations/bin/python -m unittest discover -s tests -v
.venv-integrations/bin/python scripts/validate_contracts.py
.venv-integrations/bin/python scripts/generate_ui_contracts.py --check
openspec validate additive-connector-extension --type change --strict --json
```

Optional desktop/mobile browser verification uses a built isolated UI copy and an offline extension backend:

```sh
BUILDER_EXTENSION_TEST_UI=/absolute/path/to/isolated/ui-copy \
  frontend/node_modules/.bin/playwright test --config connector_extension/playwright.config.ts
```

The browser harness uses API port 8013 and UI port 3313 and refuses to reuse another server. Results stay under extension state. Current verification evidence is recorded in [VERIFICATION.md](VERIFICATION.md).

New tests execute actual adapters against fake OAuth/HTTP transports and use the real Registry, canonical API, GraphRunner, action gates and trace records. They verify generalized links, prompt-driven discovery, optional multi-sheet restrictions, workflow-owned stable-ID writes, Calendar pagination/time/reminders, MIME attachments and replies, recipient denial, scope checks, private artifact isolation, uncertain-write recovery and disabled defaults. They perform no live Google request, mail submission, Calendar write, search request or workflow modification in the original database. Live consent/access/delivery still require operator setup and separately authorized acceptance actions.

Provider references: [Calendar discovery](https://developers.google.com/workspace/calendar/api/v3/reference/calendarList/list), [Gmail identity](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users/getProfile), [Calendar event creation](https://developers.google.com/workspace/calendar/api/v3/reference/events/insert), [Calendar event updates](https://developers.google.com/workspace/calendar/api/v3/reference/events/patch), [Gmail MIME sending](https://developers.google.com/workspace/gmail/api/guides/sending), [Gmail thread requirements](https://developers.google.com/workspace/gmail/api/guides/threads), [Gmail attachments](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages.attachments/get), [Brave Search API](https://api-dashboard.search.brave.com/app/documentation/web-search/query).

Procurement development now also includes an extension-only [SQLite persistence service](procurement/PERSISTENCE.md), with transactional revisions and lifecycle guards. Its opt-in first-slice service routes and gated coordinator are described below.

The opt-in [procurement first-slice coordinator](procurement/AUTOMATION.md) now connects selected requirements/vendor tables to BOQ/RFQ records, reviewed tracking-sheet projections and Gmail drafts. It adds internal tools only when `procurement_enabled` is true and preserves human action gates. Quotation, award, PO and Calendar lifecycle automation remain later work.
