# Sheets → agents → Gmail through a UI-created workflow

For generic prompt-generated checks and drafts saved back to Sheets, see [Phase 1 sheet drafts](sheet-drafts-phase1.md). That workflow adds restricted ID-based record saves and does not send customer email.

The live launcher supplies reusable provider connections. Your UI-created workflow owns the trigger range, stable ID column, priority condition, agent instructions, output handoffs, email content and optional approval gate. Starting the launcher does not create, publish or approve a workflow.

## Start the backend and UI

From the project directory, use separate terminals:

```bash
cd /home/raf/agentic-ai-builder
BUILDER_EMAIL_DIRECT_SEND=1 .venv-integrations/bin/python scripts/run_live_backend.py --port 8002
```

```bash
cd /home/raf/agentic-ai-builder/frontend
BUILDER_API_URL=http://127.0.0.1:8002 npm run dev -- --hostname 127.0.0.1 --port 3001
```

Open http://127.0.0.1:3001. Port 8000 currently belongs to another service. Use port 8002 for this backend. The explicit BUILDER_API_URL matters: the frontend otherwise defaults to the fixture backend on port 8011. Stop the previous backend with Ctrl+C before starting the live launcher on the same port. This launcher replaces the plain uvicorn command for live provider execution.

Refresh the browser after a backend restart to renew its development session. The Sheets adapter accepts a published spreadsheet URL as well as a bare ID. If a source fails before its first successful poll, rows added during that failure are included in the eventual baseline: append a new unique ID after the source recovers to test dispatch.

## Configure and verify connections

The existing private .env provides OPENAI_API_KEY, OPENAI_MODEL, GOOGLE_TOKEN_FILE, GMAIL_SMTP_USER and GMAIL_SMTP_PASSWORD. BUILDER_EMAIL_RECIPIENTS specifies the server-approved destinations. The direct-send command opts in with BUILDER_EMAIL_DIRECT_SEND=1; omitting it keeps per-action approval as the default. Existing published workflows retain their old approval nodes: edit or regenerate the workflow with the objective below and publish the new revision. Disable the old workflow if you create a replacement. This session saved aravind@bellcorpstudio.com as requested. Google OAuth files and all passwords stay local; workflows contain opaque credential references only.

```bash
cd /home/raf/agentic-ai-builder
.venv-integrations/bin/python scripts/run_live_backend.py --check \
  --sheet 'https://docs.google.com/spreadsheets/d/1GGkFxltftMGEuRnItxjFtgvPQU5rkGxeU8MLjZw4ccA/edit' \
  --range A:K
```

Checks list available models, read the selected range and perform Gmail STARTTLS/AUTH/NOOP. They send no email. If Google access fails, run `.venv-integrations/bin/python scripts/authorize_google.py` and ensure the authorized Google account can open the Sheet.

For a remote VM, run `.venv-integrations/bin/python scripts/authorize_google.py --paste-redirect --account your-account@example.com`. Open the newly printed link in your browser, choose the intended account and approve every requested permission. Scroll down to finish consent. If the browser then shows connection refused at `http://127.0.0.1:8765/`, copy that entire address into the waiting terminal's hidden prompt. The connection refusal is expected in this mode; do not paste the Google consent-page address or reuse an old link/redirect. Keep passwords and redirect URLs out of chat. The helper reports safe retry guidance and replaces the old token only after offline access and all configured permissions are validated. Sheets edit consent covers Sheets read permission; other configured scopes remain required. A web OAuth client must register the exact loopback redirect; a desktop OAuth client supports this loopback flow directly. This command does not add Docs, Calendar or Drive write scopes to your configuration.

If the browser never leaves Google's consent page after Allow, the callback has not been issued; replacing the URL manually cannot generate it. An alternative for a web OAuth client is [Google OAuth Playground](https://developers.google.com/oauthplayground/), which uses Google's HTTPS callback rather than localhost:

1. In Google Cloud Console, open Google Auth Platform → Clients (or APIs & Services → Credentials), choose the same web OAuth client used by `GOOGLE_CREDENTIALS_FILE`, and add `https://developers.google.com/oauthplayground` to its Authorized redirect URIs. Preserve the existing URIs.
2. In Playground's gear/settings, select **Use your own OAuth credentials** and enter that client's ID and secret privately. Keep OAuth flow server-side, access type offline, and consent prompting enabled. Do not use Playground's default client: its token belongs to a different client and cannot be imported here.
3. In Step 1 enter the scopes from `GOOGLE_OAUTH_SCOPES`, separated by spaces. For the current setup these are Sheets read/write, Drive metadata read, Docs read and Calendar events read. Sheets write covers Sheets read, so the redundant Sheets readonly entry may be omitted. Click **Authorize APIs**, select the intended account, and approve access.
4. On return to Playground, click **Exchange authorization code for tokens** in Step 2. Copy only the `refresh_token` value.
5. Run `.venv-integrations/bin/python scripts/authorize_google.py --paste-refresh-token` and paste it into the hidden local prompt. The helper refreshes it against Google's official endpoint and requires Google's returned scopes to cover every configured permission before saving it privately. It rejects responses without explicit scope evidence.

The alternative still requires Google consent. If Allow hangs in Playground too, try a fresh session in another browser or on another device/network; investigate browser Network errors or Google Workspace app restrictions. A Playground callback cannot resolve an underlying Google consent failure. Do not send client secrets, refresh tokens, browser session URLs or network exports in chat. The localhost callback command remains available; using Playground requires no backend/frontend restart until a token has actually been saved.

For refresh import failures, use the reported category: `invalid_client` means the client ID/secret was rejected; `invalid_grant` means the supplied refresh token is unusable or belongs to another client; `invalid_scope` requires checking the consented permissions; `invalid_rapt` indicates required Google reauthentication/session policy. Copy directly from Step 2's **Refresh token** field using Ctrl+A then Ctrl+C inside the field, and paste into the Linux terminal with Ctrl+Shift+V. The helper rejects obvious access tokens, authorization codes, client secrets and quoted/JSON values. Refresh requests omit redundant Sheets readonly when write is requested, but all original configured permissions are still checked before saving. Only share the safe terminal error line for diagnosis, never token values or request/response screenshots.

Unknown runtime models require operator-owned BUILDER_MODEL_RATES JSON keyed by the exact model ID, containing input_per_token/output_per_token. The launcher includes gpt-5.6-luna standard short-context rates, verified against the [official model page](https://developers.openai.com/api/docs/models/gpt-5.6-luna) on 2026-10-10. Configure BUILDER_MODEL_TOKENIZER only if installed tiktoken lacks the exact model. SDK retries are disabled and Responses storage is disabled, following the [Responses API documentation](https://developers.openai.com/api/docs/guides/migrate-to-responses). The planner permits at most two bounded requests, including one correction; runtime agents reserve their own budgets before calls.

## Create the workflow

n Overview, paste the spreadsheet URL into the existing Google Sheets URL or ID field. Paste this objective:

Copy only the text inside the following code block into the objective. The publication instructions and test rows below it are separate steps.

```text
Monitor new rows in the selected Google Sheet, range A:K on its first tab.
Headers: lead_id, name, email, company, industry, budget_usd, requirements,
status, priority, qualification_reason, email_status.
Use lead_id as the unique stable row identity. Require lead_id, name,
company, requirements and priority before processing. Ignore existing
rows when first activated. Do not update the Sheet.

Check priority exactly equals High with a deterministic condition before
model calls. Finish without email when it does not match.

For a matching row, use two real model agents. The analysis agent reads
the row and summarizes its requirements, business context and suggested
next steps. The writing agent consumes that summary and the row and
composes a clear notification subject and body. Include lead_id and
company in the notification. Enable every guardrail and validate each
agent's output schema.

Include a registered read_spreadsheet source capability for authorized
polling. Use smtp_send_email with a separate deterministic sender agent
to notify only aravind@bellcorpstudio.com. The row's email column is lead
contact information, not the notification recipient. Send automatically
without a human action approval gate. Set the deterministic sender
agent approval_requirements to an empty list. Keep the workflow review
and recipient restrictions before publication.
Use one bounded model call per model agent, zero retries and workflow
budgets that cover all agents. Use a 300-second workflow timeout.
```

Generate and insIpect the workflow, then Publish. Publication validates the graph and Registry assignments and activates its trigger template. Generation alone does not start polling. If the data is on a different tab, replace A:K in the prompt and check command with `'Tab Name'!A:K`.

After publication, allow at least one polling interval (10 seconds) for the baseline. Then append the complete test row below with a new lead_id. With direct-send mode enabled, a High row runs both agents and sends automatically to the approved recipient. Check Runs for completion; Approvals stays empty because this workflow has no action approval gate. The Sheet email_status cell does not control application authorization.

Tab-separated example, in the existing A:K columns:

```tsv
L012	Test Lead	lead@example.com	Demo Company	Software	85000	Automate internal sales reminders	New	High	Clear automation requirements	Pending Approval
```

Use a fresh ID for each test. Existing IDs are retained in the durable polling checkpoint, including after sorting, editing, deletion/reinsertion and server restart. Blank IDs are ignored; new partial rows wait for the required cells; duplicate IDs or missing/duplicate headers stop that poll with a visible source error. Each newly published release establishes its own baseline. Rows added before its first successful baseline are treated as existing.

Monitoring and Governance → Live governance & usage show server source health, last successful poll, baseline state, reviewed agent guardrails and runtime audit events. A source error can occur before any run exists. Usage counts workflow reservations once; token and cost counters are conservative reservations, not provider billing. Local draft policies remain separate from these server records.

The spreadsheet document title is separate from the worksheet tab name. Use the actual bottom tab name in a named range, or an unqualified range such as A:G for its first worksheet. The generic reader now recovers a missing named tab when exactly one actual worksheet exists; it never guesses between multiple worksheets. Invalid or ambiguous ranges report SHEETS_RANGE_INVALID. Authorization, header validation, stable identity and baseline rules still apply to every spreadsheet.

Tickets verification on 2026-10-10: spreadsheet title Tickets had actual tab Sheet1, so its published 'Tickets'!A:G range failed before the baseline. Generic recovery established the baseline, then an explicit test of existing Refund/Open ticket T002 through the published workflow completed as run_36580e6d169447a192e350531acc0b82, with two real model calls and one confirmed SMTP submission to the configured recipient. No Sheet cells or workflow rules were changed. Existing rows T001–T005 are now baseline identities; use a fresh ticket ID for polling tests. Category wanted does not satisfy the published category Refund condition. All 151 Python tests and contract/OpenSpec checks pass. Restart the operator-managed backend to load the generic recovery for ongoing polling.

Delivery recovery verified on 2026-10-10: the active direct-send workflow used a `row["priority"]` event path that the old dot-only mapper rejected with EVENT_MAPPING_FAILED. The mapper now safely supports literal bracket paths and publication validates that syntax. The retained checkpoint recovered two waiting High rows through two real model calls each and one SMTP submission each. Both runs completed and SMTP confirmed recipient acceptance. Inbox placement has not been verified. Restart the existing backend with the direct-send command above to load the mapping and dashboard changes for future polls; do not recreate the current workflow or reset its checkpoint.

## Verification and practical limits

The application graph orchestrates the agents and validated output handoffs; CrewAI executes each bounded model step. The model cannot directly call tools. Server policy restricts SMTP host and recipient. Per-action approval remains the default; BUILDER_EMAIL_DIRECT_SEND=1 explicitly permits this configured SMTP tool to send from a published workflow without an approval gate. Workflows that retain approval nodes still pause at them. Uncertain SMTP submission blocks without automatic resend; SMTP acceptance does not guarantee inbox placement.

Live checks on 2026-10-10 verified model availability, access to the provided Sheet and Gmail authentication. Synthetic live checks verify actual model agents without disclosing real Sheet rows. Controlled tests separately verify source polling, two-agent handoff, false-branch skipping, approval, restart/dedup, prompt-injection rejection and SMTP submission using an offline transport. Actual direct notification delivery requires publishing the updated workflow under direct-send mode and adding a fresh row after baseline. No real direct-send email has been submitted by these tests.
