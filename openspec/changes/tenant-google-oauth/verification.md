# Verification — 6 November 2026

## Local checks

- 49 backend tests passed: Google connection lifecycle, scopes, owned-token binding,
  cross-tenant denial, callback handling and existing Simpsons isolation.
- 527 frontend tests passed across 80 files, including new signed-routing/cookie
  regressions and existing proxy/login/account selectors.
- Frontend production build, TypeScript, lint, shared contracts and strict OpenSpec
  validation passed. Existing framework/dependency warnings remain.
- Staged copies of both configured client backends verified OAuth setup, all 19
  existing Google connectors, browser cookie binding and cancellation. No provider
  token exchange, model request, email, spreadsheet write or calendar write occurred.
- Controlled consent tests verify storage in the initiating tenant, missing-scope
  rejection, inaccessible foreign connections and absence of unbound-token fallback.

## Public deployment

Both dedicated client backend env files now explicitly include Google web OAuth
settings, separate encryption keys and the owned connector feature flag. Backends
and frontend were restarted. The operator backend and its four Google connection
rows were preserved. No existing Google account credentials were copied to a client.

Public HTTP verification passed for Simpsons and Subway:

- Existing login credentials authenticate independently.
- Google setup reports configured and the client account list is initially empty.
- Authorization returns both OAuth browser and signed callback-routing cookies.
- Cancellation callbacks complete without an application login cookie.
- Wrong-client assertions are rejected.
- Data metadata snapshots, ontology versions/workspaces, workflow revisions and
  client credential files matched recorded preservation hashes. Operator connection
  rows matched their original hashes.

Actual public browser checks passed on desktop and mobile for both clients:
Connect Google is enabled; scope choices open; Continue to Google reaches actual
Google sign-in; returning cancellation reaches the correct Integrations page; no
horizontal overflow occurred. No Google account/password was entered or consent
completed. Google accepted the configured public redirect despite the downloaded
client JSON's older local redirect listing.

User consent and live Gmail/Sheets/Calendar operations remain for the account holder.
This verification does not claim that a real account was connected automatically.
Private screenshots, browser receipts, HTTP checks, rollback env files, database
backups and test logs: `.local/tenant-google-release/`.

The final expanded backend regression suite passed all 98 tests, including Subway
onboarding, business planning and connected action plans in addition to Google
connection and client-isolation tests. Final shared contract validation passed.
All three deployed services are active. No real account consent or external action
was performed by the agent.
