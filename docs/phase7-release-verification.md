# Phase 7 release verification

The default `cd frontend && npm run test:e2e` now runs every browser spec with one worker against the current production build and an explicitly offline, fresh temporary test database. It never reuses a running server on 3100 or 8011. It explicitly sets test authentication/origins and disables real provider transports. Production uses different loopback ports (3001/8002).

To test an isolated production build without touching the running site's dependencies or artifact:

```bash
cd /home/raf/agentic-ai-builder/frontend
BUILDER_E2E_FRONTEND_DIR=/home/raf/agentic-ai-builder/.local/phase7-verification/frontend \
BUILDER_E2E_DATABASE_DIR=/home/raf/agentic-ai-builder/.local/phase7-browser \
npm run test:e2e
```

Clean installation, types, lint, unit tests and production build were run in `.local/phase7-verification/frontend` using the repository's unchanged package.json, package-lock.json and .npmrc. The existing npm configuration is required to reproduce this lockfile. All 530 installed package versions match the main frontend tree. Browser binaries are shared; live node_modules and the active .next directory are not replaced during verification.

The required backend command is:

```bash
.venv-integrations/bin/python -m pytest -q tests/test_workflow_api.py tests/test_lifecycle.py tests/test_runtime.py
```

Full backend/connector verification uses `python -m pytest -q tests connector_extension/tests` with `BUILDER_TEST_POSTGRES_DSN` pointing to a dedicated disposable, nonadministrative PostgreSQL test database. Do not use the production database. CrewAI and the actual PostgreSQL adapter must be installed; a skipped dependency is not passing evidence. The Phase 7 run uses the installed runtime/integration dependencies and pytest 9's built-in subtest plugin; `pip check` passes. Temporary database, role and connection state are removed after the run.

The complete isolated browser journey uses actual canonical APIs and CrewAI with an explicit offline model response. It generates a workflow, edits an agent and branch, saves/reloads, validates, obtains trusted Registry acceptance, submits/approves/publishes/activates, executes, inspects the exact run and node events, injects a controlled runtime data failure and checks stable retries/no duplicate runs. Altered agent instructions are not automatically trusted: the test server's explicit operator checkpoint calls real Registry validation under its authenticated tools.manage administrator. This checkpoint exists only in the dedicated test server when both test mode and its explicit opt-in are enabled and real connectors are off; it issues no tool grants. It is absent from production, and no production Registry policy was relaxed.

Historical execution does not substitute a current draft graph. Project communication remains accessible without a root run; open communication dialogs persist while switching runs; Workflow plan displays configured structure and Recorded run displays its exact historical revision. Existing workflow reads retain authoritative Registry readiness feedback.

The acceptance matrix and final evidence live in `openspec/changes/phase7-release-verification/`. Passing offline provider scenarios and mocked visual fixtures are reported separately from read-only production HTTPS smoke. No real email, Sheets write, production generation/run/approval/activation or provider connection probe is submitted by live verification.

Production qualification remains blocked by deferred Google Workspace production login and the unavailable supported side-effect-free simulation service. The UI states simulation is unavailable; validation and isolated test execution are not represented as production simulation. The large initial global workflow collection/overview also remains unbounded. Do not label the app production-ready based only on automated test counts.
