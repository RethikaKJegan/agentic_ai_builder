# Phase 4 verification — 18 October 2026

Implemented locally: exact-key PostgreSQL/MongoDB CRUD, server-owned field/action
policy, actual Registry tool/approval bindings, explicit reviewed execution,
encrypted evidence, durable no-replay claims, counts/history and guarded recovery.
Configuration and manual acceptance: `docs/controlled-database-crud-phase4.md`.

## Automated evidence

- `scripts/verify_database_crud.py`: 215 backend tests passed without skips,
  including disposable PostgreSQL 16 and MongoDB replica-set operations and
  existing selection, graph, source, query, pushdown, federation and job tests.
  Log: `.local/phase4-crud/backend.log`.
- Final `pytest -q tests/test_data_operations.py`: 30 passed without skips after
  further recovery, schema-lock and database-privilege cases. This overlaps the
  broader run; counts are not additive. Existing jsonschema/FastAPI deprecation
  warnings remain.
- Native coverage includes CRUD/recovery on both engines, conflicts, staleness,
  authority revocation before commit, concurrent claims, partial completion,
  successful/partial compensation, MongoDB missing-versus-null restoration,
  decimal rounding rollback, trigger/cascade rejection, concurrent CREATE TRIGGER
  exclusion and database DELETE privilege denial despite application approval.
- Commit acknowledgement loss and application publication loss cannot replay
  writes. HTTP boundaries, owner isolation, encrypted snapshots/value-free audit,
  literal SQL-looking keys/operator rejection, Registry approval fingerprints and
  PostgreSQL application-store reconstruction are covered.
- Frontend: 134 unit/domain/proxy tests, TypeScript and scoped ESLint passed.
- Isolated production build passed: `.local/phase4-crud/build.log`.
- Production Chromium fixtures: 30 desktop/mobile scenarios passed, including
  eight Operations scenarios covering both engines, disabled policy and uncertain
  outcomes. Log: `.local/phase4-crud/browser.log`. Browser tests intercept APIs;
  actual native engine tests provide separate database evidence.
- Shared contracts, generated frontend drift, operations schema/example policy,
  strict scoped OpenSpec and whitespace checks passed.

## Deployment and acceptance boundaries

At initial implementation verification, no deployment, service restart, live source
writes, credential changes or policy activation was performed. Subsequent authorized
activation is recorded below. Other targets remain disabled without explicit policy.
No physical-device, WebKit or real cloud CRUD acceptance is claimed. Generated
workflow integration remains original-plan Phase 5. No external notification or
downstream contributor acceptance is inferred.

Groups contain up to four independent single-record transactions. Cross-source
partial completion requires reviewed compensation; uncertain commits require
reconciliation and cannot be replayed or automatically recovered. Recovery depends
on current authority, unchanged after-images and retained evidence.

## Authorized running-app activation — 18 October 2026

Activated verified frontend build `zQFwuMLj3YJulWO9QmS8i` after source/configuration
parity checks. Retained 277 additional static assets and verified all 319 files from
the previous active build remain byte-for-byte unchanged. Previous build and private
environment backup are retained in `.local/phase4-crud/activation/`.

Set only `BUILDER_DATA_WRITE_POLICY_FILE` in the existing private backend environment
to `.local/database-write-policy.json`. The policy allows exactly the verified Atlas
`northwind.phase4_records` test collection with `_id` identity and four writable
fields. No PostgreSQL target was enabled. Restarted the existing Builder API, worker
and frontend services; all are active. Credentials, individual authentication
limitations, origins and shared demo identity were preserved.

Four real Chromium smoke checks passed: local/public routing on desktop/mobile,
authenticated Operations API and UI, exact target/action visibility, enabled read
control, reload and no page errors, missing assets or horizontal overflow. Responses
were not mocked; a browser guard blocked all mutations and observed none. No cloud
record read/write, model request or workflow execution was initiated by verification.
Evidence: `.local/phase4-crud/activation/result.json`, `browser.json`, and screenshots.
This does not establish physical-device acceptance or production IAM readiness.
