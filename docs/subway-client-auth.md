# Subway authentication — 6 November 2026

Live login: <https://praxi.bellcorpstudio.com/login>

The temporary Subway account uses `subway.admin@example.com` and the user-supplied
dummy password. The private credential file is `.local/tenants/subway/login.txt`.
Only its scrypt hash is loaded by the website; credentials and proxy secrets are
excluded from Git.

The existing website authentication supports operator, Simpsons and Subway
accounts. A signed session pins its client audience. Each client uses a separate
private upstream and proxy secret. The backend verifies its expected audience and
key on every request, including session bootstrap. Client endpoints cannot share
an upstream or fall back to another client. Existing Simpsons tokens retain their
original format and key configuration.

Subway runs as `agentic-builder-subway.service` on loopback port 8021, using
`scripts/subway_client.py` and its private `backend.env`. Its identity is
`client-subway` / `subway-client`. Its application store and encryption key are
separate from Simpsons. The store has an empty source allowlist, no company data,
no business-ontology workspace and no ontology versions or definitions.

This stage exposes authentication and empty read-only views. Subway has viewer
permissions and read-only workspace scope. Planning/runtime are disabled and
mutation requests return `CLIENT_NOT_CONFIGURED`. No model credentials, company
connections, source data, ontology import or ontology generation are configured.

Simpsons continues using its existing process on port 8020, source bindings,
ontology versions, credentials and workflows. Its process was not restarted for
this rollout. The frontend was rebuilt/restarted to register the Subway account
and display the correct workspace name for each client.

Verification: 32 backend tests and 194 frontend tests passed. Types, lint, production
build, shared contracts and strict OpenSpec validation passed. Public HTTPS checks
verified both logins independently, rejected cross-account passwords and foreign
backend assertions, denied Subway access to a Simpsons source, and confirmed
Simpsons still has two sources/eight ontology versions while Subway has zero/zero.
No model or company-data queries were submitted during this stage.

Private evidence: `.local/tenants/subway/public-verification.json` and
`browser-verification.json`. Rollback artifacts and preserved Simpsons credential/
configuration hashes: `.local/subway-deploy-20261106T045210Z/`.

Future Subway data/ontology onboarding requires a separately authorized change to
the authentication-only guard and source provisioning. Nothing is automatically
copied or inherited from Simpsons.
