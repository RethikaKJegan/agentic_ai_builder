# Simpsons client login

Deployed on 6 November 2026 at <https://praxi.bellcorpstudio.com/login>.
The dedicated `agentic-builder-simpsons.service` runs the API and background workers
on loopback port 8020. The website routes the Simpsons account to that instance.
The existing operator account and shared backend/worker remain in place.

Public login, the authenticated Simpsons identity, both source connections, all
eight ontology versions, anonymous rejection and foreign-workflow/source rejection
were verified. A real browser login and the desktop/mobile chat form were also
verified. One projected Simpsons engine reference was read without source writes.
The user chose to test model-backed chat personally; no live question/context was
sent to a model during deployment verification.

The temporary account is **Alex Simpsons**, `alex.simpsons@example.test`.
Its generated password is in `.local/tenants/simpsons/login.txt` (mode 0600).
No password or proxy secret is committed to Git.

## Isolation boundary

The signed website session identifies Simpsons. The API proxy exclusively selects
`BUILDER_SIMPSONS_API_URL`, creates a 60-second assertion with a separate proxy key,
strips browser identity headers and shared backend cookies, and verifies the
backend's client identity. Missing configuration, a shared upstream, wrong backend,
tampering and expiration fail closed. The shared backend rejects client assertions.

The dedicated instance uses `client-simpsons` / `simpsons-client` everywhere the
existing platform expects workspace / subject identity. It uses the existing API,
chat planning, business preparation/composition, ontology, evidence, database query,
Registry, runtime, lifecycle and worker code. There is no second execution engine.
Workers resolve the same pinned identity independently of the browser session.

The store must be separately provisioned and marked. Startup rejects mixed company
scopes and unprovisioned sources. The data-access manager also checks the immutable
source allowlist. Client requests cannot test arbitrary endpoints, add connections
or replace credentials; authorized source maintenance requires reprovisioning.
Database users should have access only to Simpsons databases at the database server.
The application cannot establish a database account's external grants from metadata.

Browser account changes invalidate persisted drafts and tab recovery copies, block
stale requests, discard in-flight responses and reload other open application tabs.

## Prepared artifacts

`.local/tenants/simpsons/` contains:

- `workflows.sqlite3`: only the two explicitly selected Simpsons connections,
  their metadata, Simpsons ontology definitions/versions and pinned policies.
- `data-source.key`: new encryption key; copied connector secrets are re-encrypted.
- `backend.env`: explicit tenant/provider configuration for the dedicated launcher.
- `frontend.env`: four settings to merge into the website's server environment.
- `login.txt`: temporary account credentials.
- `provisioning.json`: counts and source-write/model-call receipt.

The prepared store contains two source connections and eight existing ontology
versions. Version IDs, knowledge hashes and saved definitions are retained.
Shared workflows, integrations, business histories, queued work and arbitrary
workspace context are excluded. This preserves functionality; it does not migrate
shared execution/approval authority. Existing shared records remain in their store.
Additional approved Simpsons context documents can be explicitly selected with
`--knowledge-id`; none were inferred from names or copied wholesale.

To reproduce into a **new** directory:

```sh
.venv-integrations/bin/python scripts/prepare_simpsons_client.py \
  --source .local/workflows.sqlite3 --source-env .env \
  --directory .local/tenants/simpsons-new \
  --workspace local-workspace --owner local-builder \
  --connection-id dbconn_897964ed8cd9de2073f5497b50b80361 \
  --connection-id dbconn_1abe80b38381eaf39b4fff79b924410a
```

The scripts never overwrite an existing target. A partial failed provisioning has
no valid marker and cannot start. Review and remove failed private outputs before
reusing a path. Only explicitly bound source IDs are accepted, not name matches.

## Deployment

The deployment is active. The commands below document reproduction and maintenance.
The rollout backup is `.local/simpsons-deploy-20261106T043716Z/`; it retains the
previous frontend environment/build and the predeployment Simpsons application DB.
Public and browser check receipts/screenshots are in `.local/tenants/simpsons/`.

Validate without workers, listeners or live provider calls:

```sh
.venv-integrations/bin/python scripts/run_simpsons_backend.py \
  --config .local/tenants/simpsons/backend.env --check
```

Run the existing API and workers in the dedicated process:

```sh
.venv-integrations/bin/python scripts/run_simpsons_backend.py \
  --config .local/tenants/simpsons/backend.env --port 8020 --role combined
```

Alternatively launch separate processes with `--role api` and `--role worker`,
using the same private configuration/store/key. Bind the API to loopback and do
not expose it through a generic public backend route. The launcher reads JSON
values directly and clears inherited shared integration settings; do not source
the shared `.env` into the tenant process. Configure exact frontend origins for
the private proxy using the existing deployment origin policy.

Merge the generated `frontend.env` settings into the existing Next.js service's
private environment, retain its current operator login/signing configuration,
then build/restart that frontend under the normal release process. Do not replace
the entire website environment with this four-setting file. Changing the email
requires updating `BUILDER_SIMPSONS_LOGIN_EMAIL`; the password hash uses the same
scrypt format as the operator login. Rotate both password and proxy key before
handing the temporary account to a real client.

The prepared configuration enables the complete business chat, query and agent
workflow with the existing model configuration. Google/SMTP integrations require
separate Simpsons accounts/credentials. To enable the existing legacy provider
bundle explicitly set `BUILDER_CLIENT_INTEGRATIONS=configured` and supply its
tenant-only Google token, SMTP account and destination configuration in the private
backend file. Never reuse the operator's broad Google token or mail credentials.
Connection-based OAuth management remains available through the existing APIs.

Provider webhooks need a dedicated ingress that selects this backend and injects
its assertion while retaining each provider's existing signature validation.
The anonymous shared webhook URL deliberately remains attached to the shared
backend. The core chat/query/runtime workflow does not require webhook ingress.

After activation verify `/api/backend/session` returns mode `client-isolated` and
subject `client-simpsons` / `simpsons-client`, that only the two bound sources and
Simpsons ontology are visible, and that foreign source/workflow IDs fail. Test
a supported real Simpsons question and review its cited evidence before client use.


## Google integration update — 6 November 2026

Owned Google connections are now enabled with explicit tenant-local OAuth settings
and a separate encryption key. The engineering workspace's accounts are not shared
into Simpsons. Use Integrations → Connect Google, grant the desired scopes and select
the resulting account in workflow setup. See [tenant Google connections](tenant-google-connections.md)
for callback routing, workflow binding, deployment and verification details.
