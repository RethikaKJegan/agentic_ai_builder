# Agentic AI Builder frontend

The active frontend is the Mesh UI from `../incoming/pixel-perfect-match-latest.zip`, migrated to Next.js App Router. It supersedes the old `../agentt.zip` baseline. React, Tailwind, the cinematic landing, and the workflow editor are retained.

## Run locally

Use Node.js 22 or newer. Run from this directory:

```sh
npm ci
npm run dev -- --hostname 127.0.0.1
```

Open http://localhost:3000. For production, run `npm run build` then `npm start`.

## Verification

```sh
npm run typecheck
npm run lint
npm test
npm run build
PLAYWRIGHT_BROWSERS_PATH=.browser-cache npx playwright install chromium
npm run test:e2e
```

The browser suite starts Next.js on port 3100 and an explicitly test-only FastAPI/planner server on port 8011. Install the Python requirements into `../.venv-integrations/` first. Tests use a temporary repository-local database and never call providers/connectors. Package and browser caches stay in this directory. The npm legacy peer resolver is configured because npm 10's default resolver crashed on the archive's optional Vitest peer graph.

## Current behavior

- Create, edit, rename, duplicate, and delete local workflow drafts.
- Add steps, agent hierarchies, and reusable patterns; use layout tools and undo/redo.
- Search and navigate the workspace on desktop and mobile.
- Configure local agent and policy drafts and use template/agent library assets.
- Browser drafts use `mesh-local-drafts-v1`. Existing archive demo storage is neither loaded nor deleted.

Simulated AI generation, connector setup, publishing, test runs, approval decisions, role switching, demo reset/checklists, and pretend knowledge uploads are removed. Backend-dependent pages show unconnected states. Landing-page illustrations remain clearly marked as previews.

## Workflow API

Start the planned FastAPI boundary from the repository root in a separate terminal:

```sh
.venv-integrations/bin/python -m pip install --cache-dir .pip-cache -r requirements.txt
BUILDER_DEV_AUTH=1 .venv-integrations/bin/python -m uvicorn workflow_api.main:app --host 127.0.0.1 --port 8000
```

Then start Next.js as above. `/api/backend/*` forwards same-origin requests to `http://127.0.0.1:8000`; an optional server-only `BUILDER_API_URL` changes the destination. No provider keys reach the browser.

Development authentication is opt-in. It issues an HttpOnly/SameSite session for a server-configured identity and defaults to the builder role. This is a local POC session, not a production login system. Bind both servers to loopback. `BUILDER_DEV_ROLES` configures trusted development roles (builder/viewer/approver/admin); there is no browser role switch. Default builders can plan, save, read and validate, but cannot approve, publish or execute.

Planner proposals use Suprajha's production OpenAI provider and are saved as canonical draft revisions before opening the canvas. Planning is available only when the server has provider configuration; failures show safe errors. Configured, registered agents and exact authorized tool assignments can now be approved/published with server permissions. Missing assignments, changed configurations, unavailable/risky tools and pending approvals remain blocked. Run execution and runtime approval decisions remain unavailable until Rethika supplies those services.

To configure Aravind's registry, place operator-approved metadata in a repository-local JSON file and set `BUILDER_REGISTRY_CONFIG=.local/registry.json` when starting FastAPI. See `../docs/contributors/examples/harihar-registry-config.json` for an empty template and `../docs/contributors/harihar-api.md` for all fields. It is not loaded by default. Add complete accepted agent/tool definitions, explicit workspace policy, connector scopes and bindings for the exact saved workflow revision. Opaque credential references do not establish a live connector connection. Do not put raw credentials or invented approval evidence in this file. Default local sessions remain builder-only; publication requires explicit server-configured admin permissions.

Saved canonical revisions and mutation retry records live in `../.local/workflows.sqlite3`. SQLite is the local POC storage adapter; production PostgreSQL integration is pending. Server workflows and agents are excluded from browser draft persistence. Local unsaved drafts remain clearly labeled. Mutation keys persist as hashes/opaque keys without prompts or workflow documents.

Client types/validators are generated from the authoritative contracts:

```sh
# From the repository root
python3 scripts/generate_ui_contracts.py
python3 scripts/generate_ui_contracts.py --check
.venv-integrations/bin/python -m unittest discover -s tests -q
```

See `../docs/contributors/harihar-api.md` for routes, DTO mappings, service ownership and remaining dependencies. `incoming/mesh-nextjs-final.zip` records the earlier UI migration baseline; active API integration source is in this repository.
