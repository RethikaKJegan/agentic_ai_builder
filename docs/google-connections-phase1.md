# Google connections — Phase 1

Implemented: web OAuth account management under Integrations. Existing procurement token files, SMTP credentials, tool grants and execution bindings are unchanged. New connections are not yet selected by workflow tools (Phase 2).

## Server configuration

Install `requirements-google-connections.txt` alongside the deployment's current requirements.

- `BUILDER_GOOGLE_CLIENT_FILE`: server-only JSON containing a Google OAuth **web** client.
- `BUILDER_GOOGLE_KEY_FILE`: private file containing a Fernet key. Preserve and back it up securely; replacing it makes saved connections unreadable.
- `BUILDER_GOOGLE_REDIRECT_URI`: exact registered callback, for this deployment:

```
https://praxi.bellcorpstudio.com/api/backend/integrations/google/callback
```

The existing server client file lists only `http://localhost:8000/auth/google/callback`. An administrator must add the public callback above under the same client's Authorized redirect URIs in Google Cloud (Google Auth Platform → Clients, or APIs & Services → Credentials). Keep previous callbacks if still used. The local client JSON is informational about registered URIs; downloading the updated web client file removes the UI warning. Do not paste the client secret or tokens into chat or browser forms.

Configure the consent audience and test users when the app is in testing. Enable the Gmail, Sheets and Calendar APIs for later operations. Some requested scopes have Google publishing/verification requirements. Account linking is distinct from site login.

**Current deployment identity:** the Builder uses a shared local-development/demo subject. Ownership checks use that authenticated workspace and subject, so all visitors sharing that identity share its connections. Use test accounts only. This phase does not implement individual production login or claim isolation between people sharing one identity.

## UI test sequence

1. Open Integrations → Google accounts → Connect Google.
2. Select requested capabilities (or none for identity-only), then Continue to Google.
3. Select a test account and approve. On return, check its email and actual granted permissions.
4. Refresh the page, then verify that its record persists. Verify connection refreshes credentials and reads account identity only; it does not send mail or test each Google service.
5. Manage access: request an additional capability and select the same account. Unticking is not revocation. If another account is selected, no existing account is replaced.
6. Connect a second account with Connect Google. It receives a separate record.
7. Disconnect one account and check its disconnected state. Local credentials and pending managed authorizations are invalidated. This does not revoke the Google application grant or existing procurement credentials.
8. Reconnect that record with its original account.
9. Cancel consent, retry an expired callback, or replay a callback: no account should be falsely connected.

## Implementation and API

- `workflow_api/google_connections.py`: additive component migration 1, encryption, identity validation, actual scopes, durable ownership, single-use hashed states, PKCE, nonce, refresh and audit.
- `workflow_api/google_connection_routes.py`: authenticated API and narrowly scoped browser-bound external callback.
- `frontend/src/features/workflows/GoogleConnections.tsx`: account management UI.
- `shared/contracts/integrations/google-connections-v1.schema.json`: additive public record contract. Existing authoritative workflow, agent and tool schemas unchanged.

API routes: `GET /integrations/google/connections`; `POST /integrations/google/authorize`; `GET /integrations/google/callback`; `POST /integrations/google/connections/{id}/{authorize|verify|disconnect}`.

Only the exact GET callback bypasses the shared application session on a cross-site navigation. It still requires a ten-minute single-use transaction bound to its initiating browser cookie, user and workspace. Callback redirects use a fixed configured origin. Tokens, authorization codes and provider error text are never reflected in API responses; upstream callback query strings are removed from access-log scope. Do not enable query logging of the callback at the outer reverse proxy.

Refreshes are serialized by the existing database write transaction and have bounded provider timeouts. This favors correctness for a demo; a dedicated per-connection lease can avoid blocking unrelated writes under high load. The encryption key has a separately configured key file; automated key rotation is not included. Disconnect blocks new resolution; requests already sent to Google cannot be undone.

The migration is additive and supports the current SQLite/Postgres-shaped storage adapter. Live PostgreSQL and real Google consent require their configured external services; mocked tests are not evidence of live account authorization.

The frontend also needs `BUILDER_GOOGLE_RETURN_ORIGIN=https://praxi.bellcorpstudio.com` in its server environment (or frontend `.env.local`). This narrowly allowlists the OAuth return destination through the existing loopback gateway; it does not authorize public-origin mutations on other routes. For a local deployment, use the local origin and register its exact callback instead.

## Deployment verification

Deployed October 17, 2026. The exact callback Nginx location from the supplied snippet is installed with callback access logging disabled. Public UI and callback cancellation/replay were verified. A real navigation to Google's authorization endpoint returned **redirect_uri_mismatch**, so registration of the public callback is confirmed outstanding. This requires access to the Google Cloud project; changing only the local JSON does not register a callback.

Frontend strict typecheck, lint, production build and 28 focused UI/proxy tests passed. Twelve backend OAuth tests passed, including encryption, ownership, persistence, nonce validation, replay, scope accuracy, refresh coordination and disconnect races. Existing authentication regression suite passed. No successful live consent or connected-account operation is claimed until the external callback registration is completed.
