# Phase 1: prompt-generated checked drafts saved in Sheets

The same planner/runtime handles restaurant complaints, manufacturing defects and other record workflows. Agent roles, matching IDs, supporting sheets, draft instructions and status labels come from your setup prompt. The application supplies tools, permissions and budgets. This phase saves drafts; it does not require email submission, inbox reading, web search or creating/deleting spreadsheets.

## Operator setup

Use existing tabs with unique nonempty headers and stable text IDs. Each authorized write table uses an explicit bounded range containing a header row, such as `Reviews!A1:F1000`. Make sure the worksheet actually has the configured row/column capacity. Read ranges and write ranges can differ. Different spreadsheets are supported by passing their IDs and authorized ranges in the prompt.

Enter the spreadsheet URL or ID, tab ranges, ID columns and desired output columns in the UI setup prompt. The planner saves these as `metadata.sheet_write_targets` in the generated workflow. Open **Sheet write access** in the workflow editor to review the destinations before Publish. You can use another accessible spreadsheet in another prompt without editing `.env`.

You do **not** need `BUILDER_SHEETS_WRITE_TARGETS` for normal use. Leave it empty or remove an old value so it does not restrict new workflows. It is now an optional operator restriction. The example below shows the settings the planner generates from your prompt; you do not need to paste it into `.env`.

```json
[
  {
    "spreadsheet_id": "YOUR_SPREADSHEET_ID",
    "range": "Reviews!A1:F1000",
    "identity_column": "review_id",
    "writable_columns": ["status"],
    "allow_create": false
  },
  {
    "spreadsheet_id": "YOUR_SPREADSHEET_ID",
    "range": "Followups!A1:F1000",
    "identity_column": "review_id",
    "writable_columns": ["order_id", "findings", "subject", "body", "status"],
    "allow_create": true
  }
]
```

For automatic saving after workflow publication, set `BUILDER_SHEETS_DIRECT_WRITE=1` once. Omitting it retains per-action approval. This setting grants no email permission and does not remove approval gates already saved in older workflows. Regenerate or edit/review a new revision to change that behavior. A writer with no reviewed workflow targets fails closed. Optional environment targets can only restrict the workflow's destinations and columns; older workflows can retain their existing environment settings.

The Google account needs edit access and OAuth consent with `https://www.googleapis.com/auth/spreadsheets`. This consent is a one-time connection setup, not a setting for every spreadsheet. Add that scope to the existing `GOOGLE_OAUTH_SCOPES` configuration, preserving the other scopes you need, then run `scripts/authorize_google.py` if the current token lacks write consent. Registry scope labels are internal policy labels; listing `spreadsheets` in Registry is not Google consent. Credentials remain private and are not supplied in workflow prompts.

Start or restart the existing live backend with `scripts/run_live_backend.py --port 8002` and the existing frontend configuration described in [Sheets/Gmail](sheets-gmail.md). The current launcher still requires its existing model and Gmail configuration even for draft-only workflows; this phase does not change that bootstrap requirement. `--check` remains read-only and cannot prove write access. Do not run a second backend against the same provider/database.

Workflow generation has a separate 180-second model deadline, configurable through `BUILDER_PLANNER_TIMEOUT_SECONDS` between 30 and 300 seconds. Runtime call limits and zero SDK retries remain unchanged. Timeout/connection errors are reported explicitly; invalid generated drafts show validation requirement codes after the bounded correction attempt. Fresh generated drafts combine disjoint setup constants and changing values into one input mapping and close explicitly declared save-field output objects when that restriction was omitted. Saved workflow semantics are unchanged. Restart the backend and refresh the UI after updating the code.

## Restaurant setup prompt

Populate these headers first:

- `Reviews`: review_id, customer_name, email, order_id, complaint, status
- `Kitchen`: order_id, prepared_at, dispatched_at, notes
- `Followups`: review_id, order_id, findings, subject, body, status

Replace the ID in this setup prompt and generate from Overview:

```text
Monitor new rows in spreadsheet YOUR_SPREADSHEET_ID, Reviews!A1:F1000.
Use review_id as the unique stable identity. Require review_id, order_id,
and complaint. Ignore existing rows on first activation.

Generate a dynamic master and suitable specialist definitions from this
objective. The master delegates a lookup of the incoming order_id in
Kitchen!A1:D1000 in the same spreadsheet. Use actual Google Sheets read
results, not assumed facts. Report missing or duplicate order records as
needing staff review. Check the kitchen record before drafting. A recorded
delay is evidence of a delay, not proof of the cause of cold food.

Delegate a polite customer follow-up draft using the complaint and returned
findings. Do not send any email. Do not create or delete tabs or spreadsheets.
Return a schema-validated final output with separate scalar-field objects
for the follow-up record and source status. Keep review_id from the incoming
row as the deterministic save identity.

Use google_sheets_upsert_record with registered deterministic save agents
after master synthesis. Save order_id, findings, subject, body and status
in Followups!A1:F1000 keyed by review_id, then update only status in
Reviews!A1:F1000 keyed by review_id. Use Draft ready for checked drafts and
Needs staff review for missing or ambiguous order evidence. Save automatically
under the configured reviewed Sheets policy, with no per-action approval
gates when the server permits it. Keep publication review and all guardrails.

Configure sufficient master rounds and cumulative model/tool/token/cost
budgets, zero retries, and a 300-second workflow timeout. Each specialist
that reads a tool needs a model turn to request it and another to interpret
its output. Each save reserves one tool call. Include the authorized Sheets
read capability for source polling. Persist all tab locations during setup.
```

Review generated roles, schemas, mappings, save destinations, budgets and permissions, then Publish. After source health shows ready and the first baseline is complete, append a fresh unique review ID. Monitoring should dispatch the case, the master should delegate reads/drafting, the result should appear in Followups, and the original status should update. Inspect Runs and Agent communication for actual handoffs and tool results. Generation alone does not activate monitoring.

## Manufacturing variation

Use the same configuration shape with your actual tabs and columns: for example `Defects`, `Quality` and `Followups`, `case_id` as the complaint identity, and `batch_id` to match supporting records. Your prompt asks for quality-record checks and a customer draft instead of kitchen checks. No execution code or fixed role names change.

## Record write behavior and limits

`google_sheets_upsert_record` accepts spreadsheet_id, range, identity_column, identity and a scalar-valued fields object. Graph save locations must be setup constants matching approved targets. Each invocation also checks the server target/column policy. Existing records are resolved by ID at call time; duplicate IDs/headers, forbidden fields, absent update-only records and full tables fail visibly. Only changed permitted cells are written; other cells remain untouched. New records get the supplied identity. Repeating the same save does not create another row.

The implementation uses [Google's batch values API](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/batchUpdate) with RAW input, storing draft text literally rather than as formulas. Supporting reads are interpreted by generated specialists; schema checks do not establish model factual accuracy, so inspect findings and retain staff review for uncertain evidence.

File locks coordinate cooperating application processes sharing `.local/sheet-record-locks`. They do not protect against external editors sorting/writing between the read and write, or separate hosts without shared locks. Avoid concurrent external structural edits during saves. Two saves to separate targets are not one transaction: if the second fails, the first may already exist and the run records failure; no rollback is claimed. Uncertain writes are never automatically replayed. The existing lifecycle deduplicates completed source IDs across restarts; editing the same source ID does not retrigger this new-row workflow.

Tests use actual planner parsing, Registry, publication, durable polling, bounded CrewAI and the record connector with simulated model/Google responses. Passing them demonstrates code behavior, not live Google consent, live model accuracy or a deployed workflow. Live verification requires your configured targets and a controlled fresh test row after restarting and publishing.
