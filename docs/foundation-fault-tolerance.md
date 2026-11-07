# Foundation fault tolerance and operator recovery

Local implementation and controlled verification, 6 November 2026 (IST).
See [verification and component status](../openspec/changes/foundation-fault-tolerance/verification.md)
for commands, counts, coverage and infrastructure blockers. No deployment or
production migration is included.

## Execution protections

Graph dispatch, result commits, delegated success/failure and model-usage
settlement require running state, the original worker token and a live lease.
Dispatch rechecks the approved workflow digest and current Registry grants after
intent persistence. A live lease cannot extend an agent or workflow deadline.
Late or uncertain effects retain their intent, conservative usage and history;
they do not silently become completed checkpoints or new invocations.

Approval timeout policies support stop, bounded retry or a declared branch.
Unknown policies, timeout controls on other node kinds and missing timeout/error
paths fail document validation. Independent DAG paths are scheduled by the
existing graph runner; concurrent specialist work remains bounded by the existing
delegation executor. No new concurrency or loop semantics are introduced.

## Operator reconciliation

1. Use authenticated `GET /runs/{run_id}/recovery` with existing `runs.view`
   permission. The read-only response provides the workflow revision, original
   invocation/effect references, consumed usage, completed checkpoint hashes,
   local failures without an invocation intent, and calls with uncertain outcomes.
   Other workspaces cannot inspect the run. Unknown query flags are rejected.
2. If a worker lease is active, wait for it to finish or expire. Preserve the
   original exact approved action payload, workflow revision and effect reference.
   A trace preview may be truncated: do not reconstruct a payload from its preview.
3. Check the owned provider and existing connector journal. A local timeout or
   missing receipt is not proof that the provider rejected the operation. Never
   clear a journal, change its key, fabricate a receipt or resubmit blindly.
4. For spreadsheet setup, use the existing operator command. Report exports now
   support their original runtime identity and explicit workspace:

   ```sh
   PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B \
     -m connector_extension.reconcile_sheet_setup \
     --config /private/approved-extension.json \
     --input-file /private/exact-reviewed-inputs.json \
     --tool extension_sheets_create_report \
     --workspace ORIGINAL_WORKSPACE --workflow-id ORIGINAL_WORKFLOW --version 1 \
     --effect-id ORIGINAL_RUN:ORIGINAL_NODE --spreadsheet EXISTING_SPREADSHEET_ID
   ```

   Run only against the intended operator-owned connector state and credentials.
   The command verifies the original intent, provider markers, manifest, headers
   and report cells through provider reads. Only the local journal/resource
   receipt changes; it makes no provider mutation. Wrong workspace, effect or
   content is rejected. `--effect-id` is mandatory for reports. Legacy create and
   add-tabs commands retain their existing invocation and default workspace.
5. This command does not resume a blocked workflow or authorize downstream work.
   Preserve its verified receipt for an explicitly reviewed continuation that
   reuses the existing result instead of creating it again. The targeted runtime
   recovery service continues refusing write replay. SMTP/Gmail/Calendar and other
   outcomes without an implemented verifier require independent provider/operator
   investigation; this phase adds no universal remote reconciler or absence proof.

Cancellation cannot retract an action already accepted by a provider. There is
also an unavoidable interval between final authorization checks and an external
request: cancellation in that interval is treated as in-flight execution. The
runtime prevents unauthorized downstream completion and retains uncertain intent
for review; it does not promise universal exactly-once external delivery.

## Verification boundary

Fault tests terminate execution with a `BaseException` at real transaction,
transport, journal and checkpoint boundaries, then reconstruct services over the
same disposable persistence. These are deterministic crash simulations, not a
multi-host power-loss or production load test. Actual CrewAI runs use controlled
model responses, and provider effects use offline transports. Customer isolation
tests use disposable customer identities/stores, not production company records.

PostgreSQL qualification requires a private `BUILDER_TEST_POSTGRES_DSN` for a
disposable test database. The role must be able to create/drop its isolated test
schemas, without superuser, role-creation or database-creation privileges. Do not
use production connection files. Missing infrastructure leaves those tests
explicitly skipped. Multi-active scaling and unified account graph expansion
remain Phase 2 work.
