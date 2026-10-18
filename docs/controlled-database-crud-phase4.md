# Original-plan Phase 4: controlled Atlas/Supabase CRUD

The Operations tab supplies direct, explicitly reviewed database tools. It is
separate from historical query-pushdown Phase 4 and from Phase 5 workflow wiring.
Existing Questions remains the bounded search/filter/aggregate read interface.

## Supported operations and authority

Create/read/update/delete each address one explicit stable-key record. A reviewed
group contains at most four distinct targets and may span both engines. Primary
keys/identity fields cannot be changed by update. PostgreSQL uses the complete
current primary key; MongoDB uses `_id` with a supported scalar identity, including
ObjectId represented by a 24-character hexadecimal input string.

Targets are disabled by default. `BUILDER_DATA_WRITE_POLICY_FILE` points to trusted
operator JSON with exact workspace, subject, connection, dataset, identity fields,
writable fields and allowed operations. There are no wildcard grants or browser
policy editors. Malformed/duplicate policies fail closed. Source credentials stay
encrypted in existing owned connection records and must independently authorize
the database action. Discovery/read access does not imply write privileges.

Direct console reads require tools.read/tools.assign and workspace:read. Writes
additionally require workspace:write, workflow.approve and an admin/approver role.
Each action actually registers its provider tool and deterministic controller in
RegistryService, assigns the exact operation-ID/step-index schema, binds the exact
dataset destination and credential reference, applies real caller approval to the
exact assignment fingerprint, and revalidates it. No model call or invented human
identity is used. These are direct-console bindings; generated workflow/runtime
consumption is Phase 5. Tools use the existing tool contract; the additive API/
policy contract is `shared/contracts/data-sources/operations-v1.schema.json`.

The existing shared local demo identity still means multiple people using that
identity share its allowed targets. This phase does not add individual login/IAM.

## Configuration for a dedicated demo

1. Create isolated test datasets externally using database administration tools.
   For example, use an ordinary PostgreSQL table with explicit `id text PRIMARY
   KEY`, `name text NOT NULL`, `amount numeric(12,2)`, `enabled boolean`, `version
   integer`, and a flat MongoDB collection with corresponding scalar fields and
   `_id`. Seed one representative MongoDB document so profiling discovers fields.
2. Connect/profile both sources through existing Connections. Copy actual
   connection and dataset stable IDs from the detailed graph; use actual native
   field names in policy. Complete keys, field types and permissions must match.
3. Copy `docs/examples/database-write-policy.json` to a private project-local file,
   replace the placeholders and review every target/operation/field. Remove any
   operation that should not be granted. Put no URI, password or token in it.
4. Set `BUILDER_DATA_WRITE_POLICY_FILE` to that file in the backend's managed
   environment. Existing source credential encryption/TLS configuration remains.
   Loading a new environment variable requires a normal managed backend restart;
   policy contents are then reread on each action. On 18 October 2026, the user
   authorized activation on the running Builder app: the verified Phase 4 build
   and Atlas-only `northwind.phase4_records` policy are active. PostgreSQL targets
   remain unconfigured. Existing shared-demo authentication is unchanged.
5. Use a server-authenticated account with the required existing permissions and
   scopes. Open Data Intelligence → Operations and check the exact visible grants.

PostgreSQL views, generated/identity-generated columns, inheritance/partition
routing and tables with user triggers are rejected for writes. Cascading/SET NULL/
SET DEFAULT referential-action deletes are rejected. Serial defaults do not grant
automatic key allocation: this interface always requires an explicit identity.
Delete recovery also requires every stored field to be permitted and restorable.

Point operations support flat scalar records of at most 64 discovered fields and
64 KB per snapshot. Supported non-null input types include text, exact integers
within the safe JSON range, bounded decimal strings, booleans, supported ISO dates/
timestamps, UUID and ObjectId. Binary, nested/array, mixed and unsupported scalar
values fail closed. Exact decimal amounts must be strings; floats are not accepted
as decimal input. Runtime structure/types and requested post-values are checked;
rounding/coercion of requested values aborts before commit. MongoDB requires a
transaction-capable deployment. No standalone nontransactional write fallback exists.

PostgreSQL writes also require SELECT and UPDATE privileges for their record
locking and verification, plus the requested INSERT/UPDATE/DELETE privilege.
Application policy never grants database privileges.

## Lifecycle, concurrency and evidence

Prepare captures source/metadata/policy context and before-images through read-only
calls. The immutable request and before/after snapshots are encrypted in the
application store. The public review contains identity, permitted changes and
permitted before/after fields; values never enter plaintext operation metadata or
audit. Caller-supplied SQL, MongoDB scripts and operators are not executed.

Execute requires `{confirm:true}` for the owned prepared ID. Each source transaction
rechecks current authority, scopes, credentials, metadata and policy, locks/compares
the whole current record against its preview, applies bounded changes and checks
the resulting values/count. PG uses serializable transactions and bound parameters;
MongoDB uses explicit snapshot/majority transactions without transaction-body retry.
Database RLS/privileges/constraints continue to apply. Cross-database changes have
no shared transaction or snapshot. Concurrent revocation across application and
source databases cannot be made one distributed atomic commit; checks occur before
mutation and commit.

The application persists an execution claim and running-step evidence before source
I/O. Concurrent calls and same-key retries cannot re-execute an already claimed
operation. A different intent under the same retained key returns conflict. Source
commit acknowledgement loss or application publication loss leaves an uncertain
outcome; no automatic write replay or automatic compensation occurs. An abandoned
running claim is displayed as uncertain after 180 seconds, never reclaimed.

States are prepared, running, succeeded, failed, partial, uncertain and expired.
The UI shows each step's tool, identity, outcome and matched/affected counts.
Affected counts mean records with a changed stored field state (create/delete
included); a matched update setting identical values reports matched=1, affected=0.
Audit records correlate actual approval, attempts and outcomes by owner, operation,
step and tool, with counts/times and no record values.

Prepared requests expire after ten minutes. Encrypted evidence has a 24-hour
recovery window; logical expiry is enforced even before cleanup. Metadata/retry
records last up to 30 days (abandoned running metadata remains for reconciliation).
Cleanup runs on API access, so physical removal waits while all access is stopped;
this does not erase backups/WAL. Capacity is 100 operations with live recovery
evidence per owner,
four active claims globally, 20 attempts/minute per tool/owner, four steps/group,
30-second per-tool and 90-second group budgets checked at guard boundaries, plus
bounded native statement/connect/commit timeouts. Cancellation is not introduced.
These are bounded controls, not a claim of instantaneous termination or production
capacity qualification.

## Guarded recovery

Prepare guarded recovery creates a new reviewed inverse operation for known
committed, value-changing steps in reverse order. Create reverses to delete;
update restores changed fields (including MongoDB missing-versus-null via unset);
delete reverses to create. Current inverse-operation/field permissions are required.
Preparation and execution require unchanged committed after-images. Changed records,
uncertain outcomes, unsupported restorations and expired evidence block recovery.
Recoveries can themselves partially complete across databases; they are not an
atomic rollback. One recovery intent is retained per original operation; recursive
or automatic recovery is not supported. Manual reconciliation and a new explicitly
reviewed corrective intent may be needed after uncertainty or failed compensation.

## Manual UI acceptance

Use the updated local app and dedicated allowed test records only:

1. Open Operations, select one source and enter its exact identity JSON, e.g.
   `{"id":"DEMO-001"}` or `{"_id":"DEMO-001"}` for a discovered string `_id`.
2. Choose create and enter permitted values, e.g.
   `{"name":"Demo","amount":"12.50","enabled":true,"version":1}`.
   Add operation step, then Prepare operation. Independently verify no row/document
   was inserted during preparation.
3. Review every target/change, tick the review checkbox and Execute reviewed
   operation. Compare successful state, counts and actual source values.
4. Read record and verify the exact identity. New operation clears draft inputs;
   prepare/update the same key and independently verify its changed fields.
5. Prepare an update, change the same record externally, then execute the old
   preview. Expect conflict and preserved newer values. Metadata/policy changes
   must likewise prevent stale execution.
6. Delete the test record, verify absence, then Prepare guarded recovery. Confirm
   recovery preparation itself writes nothing. Review and execute it; verify the
   record is restored. Change a committed record before recovery and verify the
   guard refuses to overwrite it.
7. Repeat for the other database. A repeated execute request for the same ID must
   return its recorded status, never repeat the write.
8. Add distinct targets from both sources to one group. In a controlled test, make
   a later step conflict after preparation. Expect partial state, correct earlier
   commit evidence and eligible guarded compensation. Never assume global rollback.
9. With grants removed or a read-only account, verify writes remain unavailable.
   For an uncertain fixture, verify no retry/automatic-recovery control appears.
10. Repeat on mobile; check review, history, record values and overflow.

Fresh verification, dependency skips and workspace-only deployment status are in
`openspec/changes/controlled-database-crud-phase4/verification.md`.
