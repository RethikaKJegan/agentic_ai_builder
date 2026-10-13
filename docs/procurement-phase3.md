# Phase 3: fulfilment monitoring and buyer-confirmed closure

Phase 3 continues the existing MESH procurement project after PO release. It is
implemented for the current simulation flow: Gmail sender/thread matching is
routing evidence, not independent real-world supplier or delivery verification.
Real procurement authority remains unavailable for this automatic adapter.

## Activate the existing POs

Start/restart the backend and frontend yourself with the Phase 2 commands. Open
your published workflow, then **Procurement setup & status → Refresh project
status**. At PO_RELEASED, enter **Buyer receiving email** and **Manager notification
email**, reminder timings, and click **Activate fulfilment monitoring** once.
This saves a versioned policy bound to the active workflow and reuses its POs.
It does not resend RFQs, awards or orders. Keep the parent workflow active.

Use a buyer account different from all supplier accounts. With your current
vendor list, `aravind@bellcorpstudio.com` is also a supplier; it cannot be used as
the buyer for this test. A separate receiving account can be the buyer, while
`aravind@bellcorpstudio.com` can still be the manager. Addresses are configured
by you; none are built into the fulfilment engine.

The existing automatic procurement server opt-in and project action mode are
reused. Activation is one reviewed setup action; there are no individual action
approvals in automatic mode. Approval-mode projects retain their action gates.
Published contacts cannot be silently changed after activation.

## Supplier and buyer test replies

Reply to each supplier's **original PO email** from its configured vendor account.
Use the actual PO number, item IDs, quantities and units. Send one stage at a
time and inspect the resulting state before the next reply. For a 50-piece
helmet order (replace the PO number with the actual one):

```text
I accept PO [ACTUAL PO NUMBER] with its existing quantities, specifications,
price and delivery terms. This is a simulation acceptance.
```

```text
For PO [ACTUAL PO NUMBER], ITEM-004: 50 pieces are packed in total.
These are cumulative packed quantities. This is a simulation update.
```

```text
For PO [ACTUAL PO NUMBER], ITEM-004: 50 pieces have been dispatched in total.
These are cumulative dispatched quantities. Tracking reference: TEST-HELMETS-001.
This is a simulation update.
```

```text
For PO [ACTUAL PO NUMBER], ITEM-004: 50 pieces have been delivered in total.
These are cumulative delivered quantities. This is a simulation delivery report.
```

The buyer then receives a separate **Confirm receipt** email. Reply to that email
from the configured buyer account:

```text
For PO [ACTUAL PO NUMBER], I confirm receipt and acceptance of ITEM-004:
50 pieces in total. These are cumulative accepted quantities. All items meet
the specifications, no outstanding shortage or damage remains, and the order
is fully resolved. This is a simulation buyer confirmation.
```

Supplier delivery alone leaves the PO open. Explicit buyer receipt/acceptance,
all accepted quantities and resolution with no outstanding exceptions are
required for CLOSED. Each order closes independently; the project becomes
COMPLETED when all required items are covered by closed orders.

## What to inspect

- **Orders** status and quantities in the setup panel: RELEASED → ACCEPTED →
  PACKED → DISPATCHED → DELIVERED → CLOSED.
- **Activity** rows with supplier/buyer role, source message and evidence.
- **Orders** tracking references, expected delivery and confirmation flags.
- Existing primary-Calendar delivery events updated with current order status;
  internal popup reminders remain internal, not supplier invitations.
- One manager closure email per closed PO, and resolved BOQ items.
- The single **Agent communication** graph, including fulfilment master,
  extraction/review specialists, actual handoffs and connector results.

The worker polls about every 30 seconds, processing bounded batches. Model calls
and provider latency can take longer. Refresh the UI to see progress. No manual
run is needed for each update.

## Exceptions and partial deliveries

Explicit cumulative or additional quantities are required. Partial quantities
use partial states; values cannot regress or exceed the previous stage or order
quantity. Ambiguous or out-of-order reports request clarification; the system
does not fabricate missing stages. Reply to that clarification with corrected
details. Historical clarification requests remain visible.

Damage/shortages and delays create an ON_HOLD exception, notify the manager and
request buyer review in a separately tracked email thread. Only the configured
buyer can explicitly resolve exceptions and return the order to its recorded
prior stage. Calendar rescheduling is allowed only if enabled and the proposed
date is within the original required deadline; a delay still requires resolution.
Price changes, substitutions and compensation are not applied automatically.

One reminder and one later escalation are sent per overdue stage. Gmail message
IDs prevent repeat processing; canonical effect receipts prevent restart resend.
SQLite commits evidence, event and PO changes together. Sheets, Calendar and mail
are separate effects, not a single transaction. Uncertain submissions stop for
reconciliation rather than replaying automatically. A disabled parent stops new
effects. Tests use simulated providers; inspect actual model extraction and
perform this controlled live test before treating the flow as verified.

## Optional new-workflow prompt addition

Append to the Phase 2 prompt, replacing the contact placeholders:

```text
Continue after PO release with automatic simulation fulfilment monitoring.
Buyer receiving email: [SEPARATE BUYER EMAIL].
Manager notification email: [MANAGER EMAIL].
Remind suppliers if PO acceptance is missing after 24 hours. Follow up on
overdue delivery and request buyer confirmation after reported delivery.
Escalate an unanswered reminder after another 24 hours.
Record Activity and update Orders/BOQ and existing Calendar events.
Handle partial quantities and exceptions without inventing earlier stages.
Do not automatically authorize revised delivery dates or commercial changes.
Close only after the configured buyer explicitly confirms full receipt,
acceptance and resolution. Notify the manager once when each order closes.
```
