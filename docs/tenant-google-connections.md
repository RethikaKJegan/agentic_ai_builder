# Google connections in isolated client workspaces

## Cause and correction

The isolated Simpsons and Subway deployments omitted the Google web OAuth settings,
so the existing Integrations screen correctly disabled Connect Google. The frontend
proxy also discarded the OAuth browser cookie on client responses. Fixing only the
configuration would therefore leave authorization completion broken.

Each client backend now explicitly configures:

- `BUILDER_CLIENT_GOOGLE_ENABLED=1`
- `BUILDER_GOOGLE_CLIENT_FILE`: a private copy of the platform OAuth web application's configuration
- `BUILDER_GOOGLE_KEY_FILE`: a separate tenant-local connection encryption key
- `BUILDER_GOOGLE_REDIRECT_URI`: the existing public `/api/backend/integrations/google/callback`

The platform OAuth app registration is reusable. Google account tokens are not.
Connections, authorization sessions and encrypted credentials remain in each
client's dedicated application database, bound to that client's workspace/owner.
The four engineering workspace connections were preserved and not copied into
client workspaces. Client users connect the accounts they intend to authorize.

The public proxy now forwards the existing HttpOnly OAuth browser cookie for client
responses. A separate purpose-signed, state-hashed, ten-minute routing cookie pins
the initiating workspace. It permits callback routing when the workspace login
cookie is absent or has changed. Forged, expired or mismatched routing evidence is
rejected before forwarding a provider code. Routing grants no workspace login;
backend state, PKCE, nonce, single-use and browser-binding checks remain in force.
Only the OAuth cookie is permitted back from a client backend, never backend login
cookies. The callback return remains a fixed validated Integrations URL.

## Workflows

The existing Google connector catalogue is registered for each enabled client.
Gmail, Sheets and Calendar tools use the existing selected-account adapter, current
ownership checks and granted-scope checks. An unbound connector has no default
Google token supplier and fails with `GOOGLE_CONNECTION_REQUIRED`. Effects, artifacts
and sheet resource records use tenant-local directories. Existing Registry and
workflow approvals continue to govern external writes.

After authorizing an account through Integrations, it appears in that workspace's
Google account selector. Users choose the account for each workflow. Consent must
be completed by the account holder; deployment does not silently authorize an
account or infer scopes from requested permissions.

The downloaded OAuth client file has an old local redirect listing. The public
callback was separately checked against Google's authorization endpoint and actual
browser sign-in flow, with no redirect mismatch. Local `callback_in_client_file`
is informational; editing downloaded JSON cannot change Google Cloud registration.

## Verification and deployment

See `openspec/changes/tenant-google-oauth/verification.md`. Private rollback settings,
database backups, preservation hashes and browser receipts are under
`.local/tenant-google-release/`. Never delete tenant Google encryption keys while
saved connections use them. Restoring the prior backend env disables this feature;
it does not transfer or remove saved accounts.
