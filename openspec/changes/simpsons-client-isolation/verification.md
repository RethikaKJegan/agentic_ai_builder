# Verification — 6 November 2026

## Authorized deployment follow-up

The user explicitly requested deployment. Installed and enabled
`agentic-builder-simpsons.service`, running the dedicated API and existing workers
on loopback port 8020. Merged only the four generated Simpsons settings into the
website environment, preserving every previous setting, and restarted the frontend
with the verified build. The shared backend and worker were not restarted.

Verified the public HTTPS login with the real temporary credentials: correct
client workspace/subject, exactly two Simpsons sources, eight ontology versions,
foreign-workflow/source 404s and anonymous-session 401. Real Chromium desktop/mobile
login and chat-form visibility passed. A single projected source reference read
verified company connectivity without writes. No live model question was submitted:
automatic approval review required explicit permission for disclosure to
`api.openai.com`, and the user chose to test the chat personally.

Private receipts: `.local/tenants/simpsons/public-login-verification.json` and
`browser-verification.json`. Backup:
`.local/simpsons-deploy-20261106T043716Z/`. Separate Simpsons Google/mail accounts
and provider webhook ingress remain optional integration configuration, as described
in the deployment guide. The workspace header/account menu now identify Simpsons.

The following records the initial implementation before rollout. The public website,
shared API and shared worker were not restarted. No live model call, company
database query or company write was used for verification.

## Backend

- Tenant/security/live-provider suites: **58 passed**,
  `/tmp/simpsons-isolation-final-affected.log`.
- Source/Registry suites: **56 passed, 10 subtests passed**,
  `/tmp/simpsons-isolation-final-data-registry.log`.
- Final tenant acceptance after HTTP retrieval and automation-restart coverage:
  **6 passed**, `/tmp/simpsons-isolation-acceptance.log` (included in the 58;
  do not add these counts).
- An earlier broader workflow/retrieval/investigation/database/source run had
  **198 passed, 6 subtests passed**, plus one obsolete lightweight source-route
  fixture failure. That fixture omitted the WorkflowService dependencies now
  required by unrelated business-route installation. Its unrelated installer is
  now explicitly stubbed; the corrected source test passes in the final 56 suite.
  `/tmp/simpsons-isolation-regression.log` preserves the original result.

Acceptance provisions a new store from a mixed-source fixture and checks source
selection, credential re-encryption, unchanged immutable ontology versions, scoped
context, foreign source denial, source replacement rejection, forged/expired
identity, shared-backend rejection and mixed-store startup failure. It uses the
real installed HTTP retrieval service with a controlled company transport, and
the real grounded planner/queue/save/validate/approve/publish/execute paths. The
deterministic graph completes and its persisted runtime subject/workspace are
Simpsons. The full configured factory and worker resolver retain the same identity;
scheduled automation subjects can survive startup but still require active,
publisher-bound server identity validation to execute.

## Frontend and contracts

Account/password mapping, signed-cookie tampering/expiry, exclusive upstream
selection, assertion verification, shared-cookie stripping, anonymous API rejection,
wrong-backend rejection and cache/account-switch tests cover the trust boundary.
Browser tests also reject old tab recovery copies, stale requests and responses
whose account changes during transport or body decoding.

The frontend API/login/browser suites passed **190 tests in 20 files**. Type check,
lint and the production build passed; build log:
`/tmp/simpsons-isolation-frontend-build.log`. Shared execution contracts and strict
OpenSpec validation passed. No contract shape was changed.

## Prepared real configuration

`scripts/prepare_simpsons_client.py` prepared `.local/tenants/simpsons/` using the
two exact bindings from the existing Simpsons ontology. Receipt: two connections,
eight ontology versions, zero arbitrary workspace-context documents, zero copied
shared histories, zero source writes and zero model calls. Credentials are
re-encrypted with a new private key. Alex Simpsons is the requested temporary
account; its password and deployment secrets are in private files, not Git.

`scripts/run_simpsons_backend.py --config .local/tenants/simpsons/backend.env --check`
passed factory initialization and five authenticated/anonymous/foreign-resource
HTTP checks against the prepared store, without starting its lifespan/workers or
making network calls. Planner/runtime are configured and only two sources are
visible. The expected foreign-source 404 can log the existing safe transaction
warning (`category=None, code=0`); the check succeeds.

## Deployment boundaries

See `docs/simpsons-client-isolation.md`. Live activation, real model/source answer
quality, database-server account grants, tenant-specific Google/mail accounts and
provider webhook ingress remain deployment checks. The shared operator's Google
or mail credentials are not inherited. Business chat/data/agent configuration is
prepared; external integrations require their own Simpsons credentials. No live
rollout or universal security guarantee is inferred from controlled tests.
