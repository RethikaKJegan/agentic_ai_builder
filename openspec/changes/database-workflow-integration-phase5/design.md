# Design

DatabaseWorkflows owns metadata catalog/enrichment, source pinning, configuration
validation and trusted runtime connectors. Query execution consumes an already
validated logical plan through DataQueries (no hidden runtime planner/model call).
Record reads and prepare/execute use DataOperations. The server registers additive
database workflow tools into the existing Registry and delegates assignment and
publication approval to its normal exact workflow binding path.

Metadata database_scope pins at most four source descriptors and the reviewed graph
fingerprint when queries are used. Browser/model source descriptors are replaced
with server snapshots during planning; imported/edited workflows must match current
owned metadata. Scope is an additional restriction, never a credential or grant.

Prepare idempotency derives from run/task invocation identity. A durable operation
link is committed atomically with the prepared operation and associates request
digest, originating run/revision and operation ID. Standalone execute refuses linked
operations, and optional operation provenance directs the UI back to Execution. Execute
requires that link plus exact adjacent runtime gate evidence and current approving
authority; invocation params cannot substitute another run's prepared operation.
Preview uses encrypted operation evidence and is fetched through owned Operations
APIs; generic runtime audit events retain references/counts, not full snapshots.

Runtime adapters bind run, workflow and current auth without database I/O inside
runtime store transactions. Approval events retain the operation reference; UI
loads its current permitted preview before enabling database approval. Operation
expiry/staleness and policy revocation are enforced again at actual execution.

Use existing hierarchy and UUID handoff machinery, adding bounded graph context as
untrusted reference data to participating agent instructions. No new scheduler,
transaction engine or fake Calendar/Gmail integration. Unsupported Google actions
remain blocked by current Registry/adapter availability.
