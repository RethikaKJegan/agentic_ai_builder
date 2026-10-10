# Personal Slack DM → Gmail

The product receiver uses Slack Socket Mode, the durable release/receipt/job store,
and the existing Registry-authorized Gmail SMTP connector. It does not use the
browser fixture server or a fake model. A deterministic mapped draft avoids a
model guessing Slack sender identities. Existing workflows remain intact.

## One-time Slack configuration

For personal DMs, install the app using the account whose DMs are monitored.
Add `im:history` under **User Token Scopes**, subscribe to `message.im` under
**Events on behalf of users**, save, and reinstall after permission changes.
Keep Socket Mode enabled. In Basic Information → App-Level Tokens, generate a
token with `connections:write`. The app Client ID and Client Secret are not the
Socket Mode credential. No public HTTP Request URL or signing secret is needed
for this receiver. See [Slack Socket Mode documentation](https://docs.slack.dev/apis/events-api/using-socket-mode/).

Open the relevant personal DM in Slack's web application. A URL of the form
`https://app.slack.com/client/T.../D...` gives the workspace/team ID and DM
conversation ID. Copy Rethika's member ID from her profile's **Copy member ID**
action if only her messages should trigger mail. A team ID starts with `T`, a
personal DM ID with `D`, and a member ID with `U` (older accounts may use `W`).
Only this one configured conversation is monitored. An empty sender filter accepts
ordinary human messages from either participant in that DM.

## Install and configure

Run these from the project root. Never paste credentials into chat or command-line arguments.

```bash
cd /home/raf/agentic-ai-builder
.venv-integrations/bin/python -m pip install --cache-dir .pip-cache -r scripts/requirements-integrations.txt
python3 scripts/set_integration_secret.py SLACK_APP_TOKEN
.venv-integrations/bin/python scripts/configure_slack_gmail.py --recipient aravind@bellcorpstudio.com
```

The setup command asks for the team, DM conversation and optional sender IDs.
It loads the existing Gmail username/app password from `.env`, writes owner-readable
operator settings and Registry metadata under ignored `.local/`, and prepares
**Slack DM → Gmail** (`slack-dm-gmail`) as an unapproved draft in the same database
as the UI. It does not send email, approve, publish or overwrite an existing draft.
Repeating setup with identical settings preserves the existing revision. Changed
source/recipient mappings require a reviewed new draft revision; mismatched setup
fails clearly rather than activating an old mapping with new settings.

## Start the real backend

Stop the previous backend with Ctrl+C, then use this dedicated launcher instead
of the bare `uvicorn workflow_api.main:app` command:

```bash
cd /home/raf/agentic-ai-builder
.venv-integrations/bin/python scripts/run_slack_gmail.py
```

This launcher loads `.env` (process variables take precedence), validates missing
configuration, connects Socket Mode and attaches the real Gmail connector before
starting the dispatch and runtime workers. It serves on loopback port 8000.
Missing tokens/settings fail with actionable errors. It disconnects and stops
workers on shutdown. Use one instance; do not run it beside the old backend on
the same port or point both at this database. The launcher enables the existing
local admin/approver development session; production authentication is separate.

In another terminal:

```bash
cd /home/raf/agentic-ai-builder/frontend
BUILDER_API_URL=http://127.0.0.1:8000 npm run dev -- --hostname 127.0.0.1 --port 3001
```

Open `http://127.0.0.1:3001`, open **Slack DM → Gmail**, and click **Publish**.
The existing button validates, approves, publishes and activates the mapped
trigger. It never sends email just by publishing. The editor's **Test** button
remains a local simulation and cannot verify Slack reception or mail delivery.

## Live test

1. Send a new message in the configured personal DM, from the configured sender.
2. Open **Approvals**. A matching event creates a run paused at **Approve email**.
   Refresh if needed; the page polls for new requests.
3. Select the run and approve its pending action. The runtime worker resumes
   under the automation identity, and SMTP submits the DM text to the exact
   configured recipient. Approval times out after 55 minutes.
4. Check **Runs** and the recipient's inbox/spam. SMTP acceptance is submission
   evidence, not proof of inbox delivery.

Duplicates share the durable receipt and job, including after restart. Bot events,
message edits, other teams/conversations/senders and disabled bindings are ignored.
Rejected/expired approval does not send. Uncertain SMTP submission blocks without
automatic resend, preventing an unconfirmed send from generating duplicate emails.

If an existing AI-generated draft still lists sender-condition or incoming-event
review requirements, merely restarting cannot resolve those expressions. The
prepared mapped draft is the ready-to-review deterministic path; existing AI
workflows must retain their own explicit mappings and bounded model adapters.
This dedicated launcher registers Gmail only, so unrelated provider workflows
should continue using their own configured backend.

## Verification evidence

Offline integration tests cover DM receipt → release-pinned job → pending approval
→ SMTP invocation, restart during approval, restart deduplication, recipient denial,
wrong sources/bot messages, rejection, uncertain send, disablement, preserved drafts,
and FastAPI startup/shutdown. These tests use a fake SMTP transport and Slack client;
they do not claim a live Slack DM or delivered email.

Recorded verification: 126 Python tests, 63 frontend tests, typecheck, lint, production build, shared contracts, generated-client drift and strict OpenSpec validation passed. Live Gmail STARTTLS/AUTH/NOOP succeeded without message submission. Slack live connection remains pending the operator app-level token and DM identifiers.

Focused browser checks: both approve and reject scenarios passed using `cd frontend && npm run test:e2e -- --config playwright.slack-gmail.config.ts`. These checks mock the API; the Python integration tests separately verify actual application lifecycle and SMTP connector logic with an offline transport.

The broader legacy browser suite was also attempted on isolated ports: 1/8 passed, 7 failed against builder controls/labels such as Create draft, Save revision and Registry review. These failures are recorded in `.local/slack-gmail-browser-tests.log` and are not counted as passing integration evidence. No builder redesign or unrelated selector rewrite was included.
