# Phase 2 backend reliability

Phase 2 addresses correction-plan sections 4–7. SQLite remains the live store. PostgreSQL migration is prepared and tested on an isolated database; changing the live persistence backend is a separate cutover. Google Workspace production login remains deferred, and public development authentication stays blocked.

## Storage and activation

Read paths explicitly use `transaction(write=False)`. SQLite read transactions enforce `query_only`; writers retain `BEGIN IMMEDIATE`, WAL and atomic idempotency updates. `BUILDER_DATABASE_BUSY_TIMEOUT_MS` defaults to 3000 and accepts 0–30000. Logs carry transaction duration, write/read type and stable failure category without SQL or bound values. SQLite busy/locked errors are contention, invalid transitions are transaction-state errors, and PostgreSQL deadlocks/serialization failures are separate categories. API errors do not automatically replay mutations.

Activation persists an operation, preparing release, inactive automation identity, triggers and preparation ownership before provider setup. Provider preparation and cleanup run outside database transactions. Finalization atomically checks the active release, published revision digest, current Registry review and permissions. Same-key retries reuse the exact operation/release. Recovery waits for the preparation deadline, then compensates with persisted cleanup state. Preparing releases cannot execute. Disable/delete deny execution and retain queued-job cancellation before external cleanup.

Runtime/model calls, delegated connector calls, trace export, source polling, effect-journal actions and activation provider calls are outside workflow database transactions. Provider reservation methods are local budget estimates. Database retries accept only explicit pure-database callbacks; uncertain SMTP/connector outcomes remain blocked for reconciliation.

## PostgreSQL boundary and SQL inventory

Install `requirements-postgres.txt` in the service environment. `BUILDER_DATABASE_URL` selects PostgreSQL for workflow/lifecycle/runtime/planning/workspace data. `BUILDER_AUXILIARY_DATABASE_URL` selects PostgreSQL for procurement records, effect journals and sheet-resource observations. Without these settings existing SQLite files remain authoritative. Configure both during a complete migration; setting only the main URL does not migrate connector stores.

`workflow_api/postgres.py` binds application values, converts the inventoried qmark/JSON/catalog/row-order/upsert constructs, preserves statement-only integrity rollback with savepoints and uses genuine read-only PostgreSQL transactions. `migrations/postgres/001_compatibility.sql` is versioned and loaded once per schema. Newer versions fail closed. Row locks guard revision/run mutations. A conservative schema-scoped advisory write reservation preserves the existing SQLite single-writer invariant, including cross-table idempotency; PostgreSQL reads remain concurrent. This compatibility implementation does **not** claim high-throughput parallel writers. Concurrent editing/activation preserves optimistic conflict checks and existing side-effect fencing.

`python scripts/inventory_builder_sql.py` regenerates the review inventory; add `--check` to check drift. It includes SQL calls and dynamic expressions across application, runtime, connectors and database scripts, literal DDL and the ten procurement subtype tables. Repeated table names belong to independent stores. PostgreSQL creates stable per-file auxiliary schemas with `workflow_api.auxiliary_database.scoped_dsn`; do not merge their `revisions`, `resources` or effect tables. Preserve identical state paths across API/worker hosts so those schema identities match. The explicit `rowid` compatibility column retains SQLite ordering; new code must not use implicit PostgreSQL row ordering.

## Migration, validation and rollback procedure

1. Record current application version/configuration, database paths and storage use. Preserve a private rollback copy of service configuration; never export entire process environments or print DSNs. Verify the target PostgreSQL role is not superuser and uses only its application schemas. Configure transport/TLS and database backups for the actual deployment.
2. Stop new edits/ingestion and gracefully stop all Builder workers before a cutover. Stop the API too for a consistent **cross-store** snapshot. A single SQLite backup is consistent for that file; independently backing up live files does not make a transaction across stores. Do not replace or delete source SQLite files.
3. Inventory `.local/workflows.sqlite3` and every actual connector state directory's `procurement.sqlite3`, `effects.sqlite3`, and `sheet-resources.sqlite3`, plus any additional inventoried SQLite files. Preserve accompanying artifact files, source uploads, policy evidence, logs and private service configuration with restricted permissions. Google tokens/credentials need the existing private backup process; they must not be included in public reports. Artifacts and cooperating file locks still require shared storage if processes run on separate hosts.
4. For **each** source, use a new private snapshot/report path:

   ```sh
   .venv-integrations/bin/python scripts/migrate_builder_database.py \
     --source /absolute/source.sqlite3 \
     --snapshot /private/new-backup.sqlite3 \
     --report /private/new-preparation.json
   ```

   Default mode takes a SQLite online backup, runs integrity/foreign-key checks, and records every table's columns, row count and SHA-256 digest. Files use mode 0600; paths are never overwritten. Null/invalid legacy primary keys and unsupported schema constructs require repair/review rather than silent coercion.
5. Prepare an **empty isolated PostgreSQL schema** per legacy database. For connector stores derive the exact schema with `scoped_dsn` using the intended deployed state path. Supply its DSN privately as `BUILDER_MIGRATION_TARGET_URL`; never pass passwords in command arguments. Repeat the command with fresh snapshot/report paths and `--apply`. The tool copies logical row order and exact values, imports indexes and foreign keys, preserves schema/user versions and serial high-water marks (including deleted event IDs), then compares every row count/digest **before commit**. A failed import rolls back target data/DDL; only versioned bootstrap metadata may remain. Nonempty targets are rejected, never truncated.
6. Inspect reports for every source and test read-only workflow/revision/run/event/approval/operation/connector records against the target. Verify existing release identity, queue/lease state and idempotency keys. Do not trigger model calls, email, sheet creation or other external effects as migration smoke tests. Retain the source snapshots and exact application/configuration rollback checkpoint.
7. Only after validation and an explicitly scheduled cutover, point **all** API/worker instances at the matching main/auxiliary PostgreSQL configuration. Start one worker owner and an API; verify health, read paths, queue counts and authorization. Keep Google Workspace/public production authentication as its own prerequisite.
8. If cutover fails **before new writes**, stop API/workers, remove the new database URL settings, restore the previous service configuration and start against the unchanged SQLite sources (or verified snapshots if sources were deliberately relocated). Retain the failed PostgreSQL target for diagnosis. Never automatically replay uncertain external effects.
9. If PostgreSQL accepted new writes, **do not switch back to an older SQLite snapshot**: that would lose edits, audit/approval evidence or idempotency. Keep services stopped, back up both stores, reconcile the delta and external effects under an explicit recovery plan. This tool intentionally does not promise automatic reverse migration after new production writes.

No live data is migrated by adding environment variables alone. Application initialization creates empty schemas; it does not import history. Missing required auxiliary evidence fails closed.

## API and worker processes

`BUILDER_PROCESS_ROLE=api` constructs provider/runtime services but starts no background group. Run `scripts/run_builder_worker.py` for a worker-only process with no HTTP listener. `combined` remains the default for existing local development. Both processes must use the same trusted server configuration, store URLs, state paths and clock synchronization.

A durable worker-group lease coordinates active/standby instances. Dispatch jobs also have expiring claim tokens; stale claims cannot execute or overwrite later/cancelled jobs. Runtime claims are renewed during in-flight work; interrupted persisted execution intents block instead of repeating an unknown external effect. Trigger receipt uniqueness and run idempotency survive restarts. The runtime worker selects indexed active statuses in bounded batches rather than loading terminal history. Provider/Registry authority is refreshed from the trusted server resolver.

Worker shutdown signals every component first and allows a bounded 180-second drain before releasing ownership. Configure the service stop timeout above this (240 seconds in the supplied rollout). Remaining queued work is durable. A call exceeding the bound may still be interrupted and require reconciliation; shutdown cannot undo external effects already accepted by a provider.

Authenticated `GET /worker-health` requires `runs.view` and reports worker/component heartbeat state, dispatch/planning backlog, active runs and local database metrics. Missing runtime tables are reported as unavailable rather than crashing monitoring. Component errors contain stable categories, not exception bodies or provider values. Heartbeats are operational observations, not a guarantee that an upstream provider is healthy. Dead worker history is retained for diagnosis; retention/alerting policy is separate operational work.

New activations always record the trusted Registry assignment subject. Legacy no-tool identities lacking that provenance fail closed in the live fresh-auth resolver and require reviewed reactivation; stored browser/admin roles are not treated as fresh authority. Existing tool-backed identities retain their recorded subject binding.

## Verification

Tests use isolated temporary SQLite files and isolated PostgreSQL schemas/role. Set `BUILDER_TEST_POSTGRES_DSN` privately to rerun real PostgreSQL checks; missing driver/database is an explicit skip, never a passing PostgreSQL claim. Provider/model/network responses in tests are offline fixtures; no live email or Sheets mutation is needed. See the Phase 2 OpenSpec verification report for exact counts and deployment evidence.
