# Real tool integration setup

All files and commands are scoped to `/home/raf/agentic-ai-builder`. Existing OpenAI values are preserved. `.env.example` contains placeholders only; do not overwrite `.env` with it. Setup and validation do not implement the agent runtime or Tool Registry.

## Local commands

```bash
cd /home/raf/agentic-ai-builder
python3 scripts/setup_integrations.py
python3 scripts/validate_integrations.py
```

Validation updates `docs/integration-validation.md` and its JSON counterpart. It emits only status and safe error categories. No email, event, Slack post, or external webhook registration occurs.

To enter a credential, run this in your own interactive terminal and enter the value at the hidden prompt. Never paste secrets into chat, command arguments, or environment examples:

```bash
python3 scripts/set_integration_secret.py GITHUB_TOKEN
```

Use the same command with `SLACK_WEBHOOK_URL`, `GMAIL_SMTP_USER`, `GMAIL_SMTP_PASSWORD`, `BREVO_SMTP_USER`, or `BREVO_SMTP_PASSWORD`. Resource identifiers can also be entered with `GOOGLE_SHEETS_SPREADSHEET_ID`, `GOOGLE_DOCS_DOCUMENT_ID`, `GOOGLE_CALENDAR_ID`, or `GITHUB_TEST_REPOSITORY`. Re-run validation after saving credentials. Avoid shell tracing, displaying `.env`, or screenshots of credential screens.

## Browser connection and manual authentication

No interactive browser automation tool is connected in this session. TinyFish was discovered as an available browser automation plugin; install/connect it to enable a browser workflow, subject to its actual ability to transfer credentials directly into local files without returning secrets through chat. Provider login, CAPTCHA, 2FA, and authorization must be completed manually. If safe local credential delivery is unavailable, use the hidden local prompts below instead. Existing connected app credentials are not exported or extracted.

### GitHub

1. Open [fine-grained token creation](https://github.com/settings/personal-access-tokens/new?name=Agentic-AI-POC&expires_in=30) and complete login/2FA yourself.
2. For the initial authenticated `/user` check, use public repository access and no optional permissions. Use an expiring token. If private repository reads are needed, select only the POC repository and add only the endpoint-required read permissions, such as Contents: read. Avoid write/admin permissions.
3. Save the token with the `GITHUB_TOKEN` hidden prompt. Set `GITHUB_TEST_REPOSITORY` to `owner/repo` if testing repository metadata access.
4. Validation performs authenticated `GET /user`, plus repository metadata if configured. It does not verify untested endpoint permissions.

Reference: [GitHub personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).

### Slack incoming webhook

1. Open [Slack apps](https://api.slack.com/apps), complete login, and create a POC app for your workspace.
2. Enable Incoming Webhooks, then Add New Webhook to Workspace. Manually authorize one test channel using the `incoming-webhook` permission; do not grant chat history or unrelated scopes.
3. Save the resulting URL with the `SLACK_WEBHOOK_URL` hidden prompt.
4. An incoming webhook has no authenticated read-only verification operation. Full verification requires your explicit approval to post a test message. The validator leaves it unverified and never posts.

Reference: [Slack incoming webhooks](https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks/).

### Gmail SMTP

1. Sign in manually to the intended Google account. If eligible, enable 2-Step Verification and open [App passwords](https://myaccount.google.com/apppasswords).
2. Create a separate app password named `Agentic AI POC`. Save your email with `GMAIL_SMTP_USER` and the generated password with `GMAIL_SMTP_PASSWORD` (remove display grouping spaces).
3. If app passwords are unavailable due to account/security policy, leave Gmail blocked. Do not weaken security restrictions. SMTP OAuth is an alternative but requires the broad `https://mail.google.com/` scope; it is not automatically added to the read-only Workspace OAuth client.
4. Validation uses port 587 with verified STARTTLS, AUTH, and NOOP. It verifies SMTP authentication only; delivery requires a separately approved email.

App passwords cannot be restricted to sending alone; they are a provider limitation rather than a send-only scope. Reference: [Google app passwords](https://support.google.com/accounts/answer/185833).

### Brevo SMTP

1. Sign in manually to [Brevo](https://app.brevo.com/). Use an existing/free account; no paid subscription or billing is enabled by this setup.
2. Open SMTP & API settings, select SMTP, and generate a dedicated SMTP key named `Agentic AI POC`. Use the SMTP login shown on that page, which may differ from your account email.
3. Save login with `BREVO_SMTP_USER` and the SMTP key with `BREVO_SMTP_PASSWORD`. A Brevo API key is not an SMTP key. Do not create an API key for this integration.
4. Validation authenticates over verified STARTTLS to `smtp-relay.brevo.com:587`, without sending. Sender/domain verification may still be needed for later delivery; DNS changes and sending are outside this setup.

Reference: [Brevo SMTP relay integration](https://developers.brevo.com/docs/smtp-integration).

### One Google project and OAuth client for Workspace

1. Open [Google Cloud Console](https://console.cloud.google.com/) and complete login manually. Select or create one POC project. Do not attach billing. Put its non-secret ID in `GOOGLE_CLOUD_PROJECT_ID` in `.env`.
2. In that same project, enable Google Sheets API, Google Drive API, Google Calendar API, and Google Docs API.
3. Configure Google Auth Platform branding/audience. Use Internal only if your Workspace supports it; otherwise External with Testing status and your own Google account as a test user. Fill the required contact fields yourself.
4. Configure only these read scopes for the current smoke checks: `spreadsheets.readonly`, `drive.metadata.readonly`, `calendar.events.readonly`, and `documents.readonly` (each prefixed with `https://www.googleapis.com/auth/`). Drive only needs metadata for `files.list`; file contents and writes remain untested. If the POC later uses app-selected files and writes, reassess `drive.file` and resource selection rather than granting blanket access now.
5. Create one OAuth client of type Desktop app. Download its JSON directly to `/home/raf/agentic-ai-builder/credentials.json`. Do not paste or show its contents. The authorization helper restricts file permissions before reading.
6. Run locally:

```bash
python3 -m venv .venv-integrations
.venv-integrations/bin/pip install -r scripts/requirements-integrations.txt
.venv-integrations/bin/python scripts/authorize_google.py
```

7. Complete browser login/2FA/consent yourself. The helper binds a loopback callback and saves `token.json` with owner-only access. No authorization tokens are printed. External testing grants may expire; reauthorization can be required.
8. Use existing readable Sheet and Doc IDs via the hidden local prompt. Keep `GOOGLE_CALENDAR_ID=primary` or supply another authorized calendar ID. Do not create sample resources without approval.
9. Validate with `.venv-integrations/bin/python scripts/validate_integrations.py`. The same token is reused for all four APIs, with refresh when needed. A client JSON alone is not API authorization.

Reference: [Create Google Workspace credentials](https://developers.google.com/workspace/guides/create-credentials).

## Public APIs and local webhook

- Open-Meteo uses the public HTTPS forecast API, with Chennai coordinates as an editable initial location. The [free endpoint is for non-commercial use](https://open-meteo.com/en/pricing); no billing is configured.
- Open Library uses a single [search request](https://openlibrary.org/dev/docs/api/search), with no authentication and no bulk fetching.
- The Generic REST API uses [JSONPlaceholder](https://jsonplaceholder.typicode.com/) with `GET /posts/1` and no authentication.
- A 256-bit random webhook secret is generated locally once and retained across setup runs. The local receiver supports `POST /webhook` with `X-Webhook-Signature: sha256=<HMAC-SHA256 of raw body>`. `python3 scripts/local_webhook.py` starts it on loopback port 8787. Validation starts a temporary loopback receiver, accepts a valid signed request, rejects an invalid signature and a tampered payload, then stops it. No external endpoint is registered. This minimal POC does not provide replay prevention or production hosting; external exposure requires additional design and your approval.

`credentials.json` and `token.json` are created only after real client download and user consent, respectively. No dummy credential files are generated. Secret files are ignored by Git; an already tracked secret would still need removal from the index and rotation if exposed.
