# Phase 2: database contention, durable activation and worker reliability

Implement correction-plan areas 4–7 in order, preserving Phase 1 and existing contention edits. Read APIs must not acquire SQLite writer locks; configuration must bound lock waits and distinguish contention from database/transaction failures. Activation must persist preparation before provider setup, perform external calls outside transactions, revalidate revision/release/authorization, and atomically finalize with durable cleanup/recovery states.

Inventory all persistence and direct SQL, add a SQLite/PostgreSQL database boundary, versioned migrations, indexes, data-preserving migration/validation/rollback procedures and actual PostgreSQL verification before claiming compatibility. Do not migrate the live database without a reviewed concrete backup/migration plan.

Separate API serving from worker execution, preserve local compatibility, coordinate worker ownership and durable job claims/leases, recover safely after crashes without replaying uncertain external effects, preserve trusted automation identity and deduplication, and expose health/backlog.

Keep Google Workspace production authentication deferred. Do not modify shared contract shapes or infer production readiness. Show exact existing-code replacements before applying edits; add meaningful regressions and report real passing/failing/unexecuted checks. Coordinate any live restart with the already deployed services; preserve active workflows and credentials.
