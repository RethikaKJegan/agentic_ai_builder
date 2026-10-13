# Procurement Phase 2: quotations, awards and purchase orders

Phase 2 extends the existing MESH procurement project. It uses supplied vendor
contacts; web research is not required. Phase 1 workflows keep their existing
behavior until a new workflow is generated with Phase 2 enabled.

Gmail replies are matched to the saved RFQ thread and sender. Message IDs prevent
duplicate extraction. A registered extraction agent reads the new plain-text
reply; deterministic checks enforce item scope, quantities, currency, line totals,
explicit charges, quote validity and the delivery deadline. Prices use decimal
arithmetic. Missing information produces a clarification request. Attachments
alone do not become quotations; send the quotation in the email body.

Comparison waits for responses from every vendor in the group or the quote
deadline. It selects a unique lowest qualifying **delivered total**, including
tax, shipping and other charges. Ties and groups without qualifying offers remain
in review. Selecting a sole qualifying offer requires the published exception.
Simulation compliance is a supplier statement, not independent certification.
Model extraction can still be inaccurate; inspect recorded evidence while testing.

Automatic simulation awards and PO emails use the published total project
spending limit and `BUILDER_PROCUREMENT_AUTOMATIC=1`. This limit is a purchasing
policy, not an API-token limit. Unknown submissions stop; they are not replayed.
Real procurement does not receive automatic purchasing authority: compliance
verification and action approval are required.

Quote deadlines and PO delivery dates create Calendar events with popup reminders.
Unanswered RFQs receive one reminder near the quote deadline. Confirmed Calendar
IDs, quotations, awards, POs and message checkpoints persist in SQLite. Quotations,
Orders and BOQ status are synchronized to the generated tracking spreadsheet.
The source Requirements and Vendors sheets remain unchanged. The existing
Procurement setup & status panel shows comparison reasons and Calendar IDs; the
single Agent communication view includes the new actions and extraction agent.
Multiple writes and sends are separate effects, not a single transaction.

## Test prompt

Create a new workflow with a unique name and your existing spreadsheet link:

```text
Create a NEW procurement simulation named "Workshop quotation test 1"
using [YOUR REQUIREMENTS AND VENDORS SPREADSHEET LINK].

Read the requirements and supplied vendor contacts, prepare the BOQ,
group suitable items and automatically send RFQs. Do not use web search.
Monitor vendor replies, extract itemized quotations and compare the total
delivered cost for the same quantities and specifications. Select the
lowest qualifying offer meeting the delivery deadline, then automatically
send the award and release its purchase order.

Use INR, delivery location Demo Warehouse, and timezone Asia/Kolkata.
The quote deadline is [FUTURE DATE AND TIME WITH UTC OFFSET].
The required delivery date is [FUTURE YYYY-MM-DD].
Authorize a total simulation purchasing limit of INR 100000 for the
whole project. Permit a sole qualifying offer for groups with one vendor.
Create quote-deadline and PO-delivery events in my primary Calendar,
with reminders 60 minutes beforehand. Run automatically without
per-action approval. Keep this a simulation and label supplier emails.
```

1. Start your backend/frontend yourself using the Phase 1 commands. The reviewed
   connector configuration must enable Gmail, Sheets and Google Calendar, with
   actual Gmail and Calendar write consent.
2. Generate the new workflow. Review the discovered source mappings, project dates,
   Calendar and purchasing policy in **Procurement setup & status**, then publish.
3. Click **Start procurement** once. No new source row is needed. Confirm RFQs
   arrived and the tracking spreadsheet was created.
4. Reply **to each original RFQ** from that vendor's address. Copy its RFQ ID and
   item IDs. Include each item's quantity, unit, unit price and line total, plus
   currency, subtotal, discount, tax, shipping, other charges, total delivered cost,
   ISO delivery date, ISO valid-until date, payment terms and specification compliance.
   Explicitly write `0` for zero charges. For competing vendors, vary shipping as
   well as unit prices to test total-cost selection. Do not invent operational facts.
5. Keep the backend running. The worker polls in approximately 30-second intervals.
   Refresh project status to inspect quotations and recommendations. Successful
   groups produce award and PO emails, Orders rows and Calendar delivery events.
6. Expected final Phase 2 project status is **PO_RELEASED**, not Closed. Packing,
   dispatch, delivery updates and buyer-confirmed closure belong to Phase 3.

Verification uses offline model/Google responses. Live consent, mailbox delivery
and actual model accuracy must still be verified with the controlled simulation.
