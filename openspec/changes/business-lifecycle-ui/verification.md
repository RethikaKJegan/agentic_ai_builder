# Verification — 4 November 2026

Implementation inventory, reused components, API mapping and user flow:
`docs/simpson-business-ontology/business-lifecycle-ui.md`.

Completed checks:

- `cd frontend && npm run test`: 72 files, **480 tests passed**, 27.51s.
- `cd frontend && npm run typecheck`: passed.
- `cd frontend && npm run lint`: passed.
- Production `npm run build` in `.local/lifecycle-ui-stage`: passed; Next 16.4.3,
  all 17 static pages generated; build `RUVN4lBRiT8k8fJPZK96M`.
  The live `.next` was not used for staging.
- `.venv-integrations/bin/python -m pytest tests/test_generic_lifecycle_phase6.py tests/test_simpson_lifecycle.py tests/test_business_cases.py tests/test_business_case_runtime.py -q`:
  **79 passed**, 22 existing deprecation warnings, 280.10s.
- `.venv-integrations/bin/python -m pytest tests/test_business_lifecycle_ui.py -q`:
  **2 passed**, two existing jsonschema RefResolver warnings, 2.09s.
- `.venv-integrations/bin/python scripts/validate_contracts.py`: passed.
- `/home/raf/.nvm/versions/node/v22.23.3/bin/openspec validate business-lifecycle-ui --strict`: passed.
- `git diff --check`: passed.

Component coverage includes both stage manifests, skipped/provisional states, all
four provenance classes, secret withholding, create/reopen/report, uncertain exact
retry, revision conflict without replay, permission restrictions, owner change,
selected stage retention after approval refresh, reviewed reassessment payload
and cancellation before preparation.

Initial browser attempts failed honestly: standard HTTP app bootstrap replaced the
controlled evidence connector. The fixture now restores its trusted evidence
connector after app bootstrap. A later browser failure exposed selected-stage reset
on validation refresh; refresh now preserves selection and stage changes clear
obsolete composition controls immediately. Neither failure was hidden by a mock
success or by relaxing backend approval requirements. Initial public smoke checks
also found Cancel incorrectly disabled for an unprepared case. The control now
permits revision-checked cancellation before preparation; component and actual
desktop/mobile browser regressions cover it. The first labelled unexecuted smoke
case was cancelled through the authenticated API after the standard session handshake.

Final `cd frontend && npx playwright test --config playwright.lifecycle.config.ts`:
**12 passed (3.2m)** in the final exact-build rerun, including cancellation before
preparation on desktop and mobile. Two tests exercise actual HTTP
Simpson and retail lifecycles on desktop/mobile; six existing dynamic and four
legacy browser tests use their established controlled route fixtures. The actual
lifecycle tests use real Registry/CrewAI/runtime with deterministic transports,
normal workflow approvals, persisted reopen, receipts, provenance, pending events,
qualified reports and memory/reassessment visibility.
No live messages, Google changes or paid model calls occur in this acceptance.

Storage: lifecycle migrations 1/2 are additive `CREATE TABLE IF NOT EXISTS` plus
migration markers. Existing cases retain pinned definitions. No destructive data
migration, environment reset, synthetic-policy publication or live retail fixture
installation is required. No new environment variable or hosting architecture.
Python backend is deployed as source under the existing virtual environment;
there is no backend packaging/build command in this repository.

Deployment completed using existing targets: `agentic-builder-frontend` (Next,
port 3001), `agentic-builder-backend` (port 8002), `agentic-builder-worker`, at
`https://praxi.bellcorpstudio.com/app`. All three services verified active. Final
frontend build: `RUVN4lBRiT8k8fJPZK96M`. Existing credentials and the attachment's
conditional authorization were used; no new infrastructure or credential changes.

The rollout verified no active execution/planning jobs, backed up SQLite, source
and the previous frontend build, restarted backend/worker, and compared exact
fingerprints: **170,531 rows across 32 persisted tables unchanged**. This comparison
preceded the intentional smoke-case creation. Lifecycle migration markers `[1, 2]`
were verified after restart. The later cancellation correction switched only the
frontend; both original and interim builds remain backed up.

Authenticated public acceptance passed through normal login and the existing API
proxy: unauthenticated session rejected; scoped case/process reads; active worker;
case creation through the UI; all twelve stages; report retrieval; persisted reopen;
memory/recovery visibility; cancellation before preparation; desktop/mobile layout;
existing Agents, Runs, Approvals, Knowledge and Monitoring navigation; and an
existing dynamic composition. **Zero browser errors and zero missing assets**.
Smoke case `case_8892526c1e70114f92540390` is explicitly labelled deployment-only,
was never prepared/executed, and is CANCELLED. The initial smoke case is also
CANCELLED. No paid model calls, live connector actions or company-source mutations
were performed during public verification.

Private backups, exact source hashes, final build/test logs, preservation receipts,
public-check JSON and screenshots: `.local/business-lifecycle-ui-release-20261104/`.
Final checks: contracts, strict OpenSpec and patch whitespace passed. No outstanding
implementation/deployment blocker. Controlled execution acceptance establishes
software behavior; actual physical warranty, shipment, engineering effectiveness
and commercial authority continue to require their configured real-world evidence.
