# Design and constraints

SQLite remains the current live persistence until migration is explicitly prepared and validated. Existing uncommitted overview-contention changes are the starting baseline, not disposable code. Provider calls, model calls and telemetry export must occur outside database transactions. Read-only SQLite transactions will use query_only to detect accidental mutations. Busy/locked failures receive bounded waits and redacted structured telemetry; they are not mislabeled deadlocks.

Activation uses a durable preparation operation and prepared release/bindings before external work, then a short final write that checks expected active release, exact workflow digest/current revision and registry authority. Recovery records cleanup pending rather than declaring an unknown provider operation successful. Same-key retries return the same operation. Concurrent preparation cannot activate conflicting releases.

Runtime execution already persists invocation intent and blocks uncertain results; retain those controls. Worker coordination must prevent both competing API replicas and replay of side-effect calls. Add persistent claims with fencing and expiration, safe shutdown, and observable backlog. No automatic retries of SMTP/connector writes.

PostgreSQL support must be verified against real PostgreSQL and the inventoried queries, not a mocked successful database. Schema/data migration must preserve run/event identities, order, revisions, approvals, idempotency and release bindings. Unknown SQL/dialect cases fail rather than silently changing semantics.
