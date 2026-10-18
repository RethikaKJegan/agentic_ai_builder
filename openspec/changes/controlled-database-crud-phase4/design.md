# Design

BUILDER_DATA_WRITE_POLICY_FILE points to trusted target entries scoped by workspace,
subject, connection and dataset, with exact identity/writable field lists and
allowed operations. No file means disabled. Reads require tools.read/tools.assign;
writes additionally require workflow.approve and an admin/approver role plus the
normal workspace:write scope. Actual RegistryService registration, assignment,
exact prepared-operation approval fingerprints and revalidation gate each tool.
Tool scopes use existing workspace:read/write, with target/field authority enforced
again by the operations service. Existing auth/workflow/agent/tool schemas stay.

Operations store encrypted request/before/after snapshots, immutable context hashes,
owner-key idempotency fingerprints and value-free durable status/audit. Preparation
is read-only; execution atomically claims before external I/O, records running
before each source transaction, and publishes each known outcome. Concurrent calls
cannot repeat work. An abandoned running claim reports uncertainty after 180 s;
it is never reclaimed for execution. Missing local acknowledgement after external
commit remains uncertain. Prepared TTL 10 min; encrypted recovery data 24 h, metadata
30 days, logical expiry enforced on access and cleanup on API use.

PG uses serializable read/write transactions, exact primary keys, row locks,
parameterized values, catalog/runtime schema checks and bounded RETURNING counts.
Mongo uses explicit snapshot/majority transactions and _id, no transaction-body
retry, full-record expected-value comparison and scalar $set/$unset. Both retain
verified cloud TLS and ownership/credential-generation checks. Errors before
commit are definite rollback; loss during commit is uncertain. Recheck current
server authority/context before mutations and commit; no distributed atomic
revocation or cross-source snapshot guarantee is claimed.

Recovery prepares a new immutable reviewed operation reversing only known commits,
in reverse order, conditional on unchanged after-images. It requires current
inverse-operation grants, rejects uncertain steps, excludes deletion with hidden/
unsupported columns or cascade/user-trigger effects, and records partial/conflict
outcomes. One recovery operation per parent; no claim of universal Undo or automatic
recovery after its 24 h encrypted evidence window. Workflow generation wiring is
Phase 5; this phase supplies a direct manual operations console and reusable tools.
