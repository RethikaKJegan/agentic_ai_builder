# Lifecycle and reviewed default policy

The machine-readable policy is `contracts/v1/policy.default.json`, revision 1. It is **definition-only**. Existing canonical Registry review and dedicated runtime write gates remain unchanged.

## Approval matrix

| Operation | Reviewed default | Conditions |
| --- | --- | --- |
| Resource discovery, source/message reads | Automatic after validation | Connected account, exact current grants, bounded inputs and approved resource scope. |
| BOQ extraction, quote checks/ranking, evidence recording | Automatic after validation | No invented facts; internal conclusions cannot authorize external writes. |
| Internal case transitions | Automatic after validation | Exact evidence, trusted actor, legal transition and transactionally checked record revision. Closure still needs explicit buyer confirmation. |
| Create spreadsheet/tabs; write BOQ/status rows | Human required | Review project, destination, headers, identity/writable columns and record-creation permission. Creation tools are not implemented yet. |
| Gmail drafts, RFQs, reminders/follow-ups | Human required | Exact recipients/body/attachments/reference; agent recommendation is not approval. |
| Awards and PO release | Human required | Current qualifying quotation/scope, terms/total, evidence and exception review; distinct approvals for award and release. |
| Calendar create/update/cleanup | Human required | Exact case-owned IDs, bodies/times and scope. Closure never grants permission over unrelated events. |
| Scope changes and single-offer exceptions | Human required | Document reason and impacted BOQ/quote/order revisions; no silent exclusion of unresolved items. |
| Bypass required evidence, delete Sheets/tabs, payments | Disabled | Outside this definition's implementation scope. |

Approval must be resolved from the trusted application identity and canonical service, not a model-provided role, local JSON row or specialist vote. Fingerprint the actual action inputs, recipients, attachments, resources, relevant source/quote revisions and policy revision. Changed content, destination, expiry, revocation or source assumptions invalidate approval. A workspace-wide workflow review is distinct from its exact external action gate. Reject/expire means stop that action; an agent cannot self-approve or silently resubmit it.

A later opt-in policy could automate bounded routine writes. It is not active, implemented or enabled by this file, and it cannot bypass the current connector gates. Any such change requires explicit operator review, defined limits and runtime implementation. Never reinterpret previously approved workflows as automatically authorized.

## State transitions and guards

`states.json` defines legal ordinary edges. Hold/cancel rules and same-state quantity updates are described there. These definitions are not runtime hooks.

| Transition / event | Required guard |
| --- | --- |
| Project DRAFT → VALIDATING → ACTIVE | Source access, complete reviewed context/BOQ and valid vendor contacts. Missing data goes to NEEDS_CLARIFICATION. |
| RFQ DRAFT → READY | Exact reviewed item scope, vendor contact, terms, deadline and reference. |
| RFQ READY → SENT → OPEN | Successful, reconciled Gmail result plus persisted message/thread; an approved intent alone is not proof of sending. |
| Quote RECEIVED → VALIDATING → QUALIFYING | Scope/quantities, arithmetic, currency, deadlines, validity and required compliance pass. Missing/conflicting evidence goes to NEEDS_CLARIFICATION; failed criteria to NONQUALIFYING. |
| Award PROPOSED → APPROVED → SENT | Current selection evidence, reviewed exception if needed, trusted approval and confirmed provider send. |
| PO DRAFT → READY → RELEASED | Approved award and complete PO snapshot; approved release and confirmed document send. Missing real commercial terms stop real release. |
| RELEASED → ACCEPTED | Reviewed supplier confirms the exact PO and quantities/terms; differing acceptance creates an exception. |
| ACCEPTED → PACKED / PARTIALLY_PACKED | Confirmed cumulative packed quantities, no more than ordered. |
| Packed quantities → DISPATCHED / PARTIALLY_DISPATCHED | Only packed items can ship; require shipment identity/tracking or reviewed explanation if unavailable. |
| Dispatched quantities → DELIVERED / PARTIALLY_DELIVERED | Supplier/carrier report tied to shipped quantities. This is not buyer acceptance. |
| DELIVERED → RESOLUTION_PENDING | Shortage, damage, rejection, conflicting receipt or missing confirmation. |
| DELIVERED → CLOSED | All ordered quantities explicitly received and accepted by a verified buyer; no unresolved defects/exceptions; explicit resolution confirmation. |
| Project ACTIVE → COMPLETED | Every required item resolved by closed orders or an explicit approved scope change. No unresolved items or holds; two closed suborders alone are insufficient. |

For each line, cumulative `0 ≤ buyer_accepted ≤ delivered ≤ dispatched ≤ packed ≤ ordered`. Unit conversions need explicit reviewed factors. Partial shipments can progress independently; an aggregate state never hides remaining quantities. Once any quantity has arrived, remain PARTIALLY_DELIVERED until all are delivered, even while later packing/shipping events update other quantities. Duplicate provider messages are no-ops. Contradictory/out-of-order events are stored as evidence and reviewed; they never blindly regress or skip state. Corrections require a new audited revision.

ON_HOLD preserves `resume_status` and unresolved issue IDs. Resume only to the recorded prior legal state after resolving the hold. Cancel released orders only with explicit human review and supplier/receipt reconciliation. Terminal records are preserved; reopening requires a separately reviewed new case/amendment rather than mutating history.

## Calendar lifecycle and cleanup

Create only requested case deadlines/milestones using the chosen calendar and project timezone. Map each event ID to project/order/purpose and record its creation result. Update existing mapped events rather than repeatedly creating new ones. Supplier status labels do not invent an expected/actual time; missing dates require clarification. Do not add guests without a separately supported operation.

After explicit order closure, eligible cleanup covers only that order's mapped events. Shared project milestones are retained until the project is complete. Persist deletion intent and result. Already-deleted owned IDs can be reconciled as complete; ambiguous IDs or calendar access failures remain pending. Calendar cleanup is independently approved under the reviewed default, and cleanup failure does not undo a valid order closure or erase its audit trail. Scope-wide Calendar clearing and unrelated-event deletion are forbidden.

## Stop conditions and recovery

| Condition | Affected action | Required response |
| --- | --- | --- |
| Missing requirements, unit/specification, address, deadline, contact or real PO terms | RFQ/real PO preparation | NEEDS_CLARIFICATION; ask for the exact missing fields. |
| Unclear table, duplicate identities, stale scope or conflicting source edits | Reads dependent on identity; writes/selection | Stop affected scope; preserve snapshots and review a new revision. |
| Missing consent/access, revoked grant, exhausted budget/quota | Provider invocation | Stop; surface the safe category; never substitute an account or destination. |
| Conflicting RFQ/PO references, unreviewed sender, quoted old content | Incoming-message processing | Quarantine for review; do not turn the message into an authoritative update. |
| Missing/invalid prices, unmatched quantities, currency/charge ambiguity | Ranking/award | NEEDS_CLARIFICATION; no guessed totals or FX. |
| Late/expired/incomplete/noncompliant offer; missing certificate | Award | NONQUALIFYING or NEEDS_CLARIFICATION; preserve reasons/evidence. |
| Single qualifying offer / tie / incomplete bid set | Selection | Human exception review; avoid claiming competitive best price. |
| Partial/damaged delivery, receipt conflict or missing buyer confirmation | Closure | RESOLUTION_PENDING; notify the reviewed manager under messaging policy. |
| Unknown provider write outcome | Retry or next dependent action | Freeze the effect and reconcile provider state before an intentional retry. |
| Sheets/Calendar synchronization failure | Projection update | Retain the source-backed case state and mark that target unsynchronized; bounded retry only when confirmed safe. |
| Simulation-only actor/compliance evidence in a real project | Real award/PO/closure | Stop; require real verified evidence. |

Read retries may be bounded by accepted runtime budgets. No automatic replay of uncertain sends, creates or other writes. A later worker must persist idempotency keys, offsets, pending reviews and sync intents before restart; this step does not start that worker.
