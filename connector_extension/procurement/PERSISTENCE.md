# Procurement persistence — Step 3

`store.py` implements a trusted in-process repository. It uses its own `procurement.sqlite3` under `.local/connector-extension/` and does not import the application, change workflow routes, call providers, start polling or migrate the earlier JSON pilot. Initialization is explicit; importing the module creates no database.

The database contains projects, BOQ items, vendors, RFQs, quotations, awards, purchase orders, fulfilment events, approvals and evidence. Scoped identities, current snapshots, immutable revisions, transaction receipts and ordered activity support restart recovery and audit. Resource links associate spreadsheets/tabs, Gmail messages/threads and Calendar events with domain records. Links are bookkeeping, not proof of ownership or deletion permission.

## Use

```python
from connector_extension.procurement.store import ProcurementStore, scope_digest

store = ProcurementStore(currency_precision={'INR': 2})
result = store.commit(
    authenticated_workspace_id, project_id, stable_transaction_key,
    [{'record': validated_record, 'expected_revision': previous_revision}],
    resources=[], sync_intents=[],
)
record = store.get(authenticated_workspace_id, project_id, record_id)
history = store.history(authenticated_workspace_id, project_id)
```

Currency precisions are explicit operator configuration; the store does not invent currencies or exchange rates. Add the actual project's comparison currency and rounding precision. Calculation uses Decimal and ROUND_HALF_UP at the configured currency precision. Unsupported currencies stop actionable transitions. Timezones are validated with ZoneInfo.

Each transaction receives complete Step 1 records and expected prior revisions (zero for new records). New records start at their defined initial state. Record IDs, types, creation timestamps and project simulation mode are immutable. Updates increment exactly once. `BEGIN IMMEDIATE` and optimistic revisions prevent concurrent lost updates. Identical retries under the same transaction key return the saved receipt; different contents under that key fail. History and completed records are preserved. Evidence and fulfilment events cannot be overwritten.

All references resolve in the same workspace/project, including records created together in a transaction. Missing references, conflicts or invalid sync intentions roll back the entire operation. PO numbers, RFQ vendor/scope identities, quote source messages, evidence snapshots and fulfilment idempotency keys are unique within that scope. Duplicate source records fail explicitly; callers handle `DUPLICATE_SOURCE` by reading the existing case rather than processing again. Stable transaction retries are automatic no-ops. Cross-mailbox and cross-project message routing remains the future ingress adapter's responsibility.

## Guards and trusted authority

The repository checks legal lifecycle edges, schema completeness, scoped line identities, current RFQ/quotation revisions, literal vendor contacts, delivered-cost arithmetic, deadlines, compliance evidence and supplier-stage evidence. `scope_digest()` fingerprints commercial BOQ fields for RFQs; changed requirements invalidate later qualification/selection. Single offers cannot claim competitive lowest cost. Awards require qualifying current quotes; release rechecks the selected award and exact approval. Order snapshots are immutable after DRAFT. Packed, dispatched, delivered and accepted counters must be monotonic and bounded. Aggregate progress cannot hide partial delivery. An order cannot close without complete accepted quantities, all confirmation flags, no unresolved exceptions, buyer evidence and a matching buyer-confirmation event. Project completion requires actual closed-order coverage or separately approved exclusions. Holds resume only to their recorded state. Released-order cancellation/amendments require a later reconciliation operation and are currently blocked.

Production authority is deliberately unavailable by default. A future authenticated application adapter must supply:

- `authority_check(evidence, role)`: independently verify the actual source, subject and asserted authority. A stored `VERIFIED_SOURCE` label alone is rejected.
- `approval_check(approval, target, operation)`: resolve the canonical human decision and verify exact action digest, workflow revision, resources, recipients, relevant source revisions and policy. The repository additionally checks decision, expiry, operation and approver role/workspace. A local approval record never mints a Registry grant.

Callbacks are trusted application code, never model-supplied flags. The adapter must authenticate workspace/project access before invoking this repository; these Python methods are not a public authorization API. Simulation-only authority is accepted only in explicitly simulated projects. The simulator cannot turn an existing real project into a simulation.

This layer validates structured claims; it does not parse email bodies, verify certificates, discover trusted identities, fetch source contents or prove that caller-supplied Gmail IDs were sent. The eventual ingestion/connector adapter must capture actual provider results and produce verified records. Source edits and revocations remain recordable, and dependent actions recheck current evidence before proceeding. The store does not perform a full bid-deadline collection policy or automatic selection.

## Synchronization boundary

Pass `sync_intents` in the same transaction as a case change:

```python
intent = {
    'key': 'projection_item_demo_r2', 'record_id': 'item_demo',
    'record_revision': 2, 'target': 'sheets',
    'payload': {'status': 'READY'},
}
```

The intent starts in `PENDING_APPROVAL` and references the exact immutable revision. `pending_sync()` exposes persisted intentions, including after restart. No dispatcher, automatic retry, provider completion acknowledgement or per-target reconciliation worker is installed in this step. Sheet writes, mail and Calendar operations still require the extension's canonical grants and action gates when a future worker dispatches them. No distributed transaction across Google services is claimed.

Run verification with:

```sh
.venv-integrations/bin/python -m unittest connector_extension.tests.test_procurement_store -v
```

Tests use private temporary databases and fictional simulation records, without Google calls. The next implementation boundary is an authenticated service/agent adapter, evidence ingestion and separately approved projection dispatch.

Step 4 now provides a limited [first-slice service adapter](AUTOMATION.md), scoped routes and approval-gated projection/draft coordination. Its source proof callback attests only selected Sheets input rows; production buyer/compliance verification and award/PO approval resolution remain unavailable. The standalone repository defaults described above are unchanged.
