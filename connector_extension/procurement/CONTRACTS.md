# Procurement domain contract v1

## Record envelope and identity

Every record carries `schema_version=procurement-v1`, `record_type`, `record_id`, `workspace_id`, `project_id`, positive `revision`, timezone-aware `created_at`/`updated_at`, `evidence_ids` and a closed `data` object. Domain revisions are separate from workflow revisions. IDs are stable opaque identities; human RFQ/PO numbers are display/correlation references, not authorization. References must resolve within the same workspace/project. Schema-valid strings alone do not establish an actual source, approved actor or valid foreign key.

All commercial quantities/amounts are bounded decimal **strings**, not binary floating-point values. Ordered/quoted quantities are strictly positive; progress counters, taxes, discounts and freight can be zero. Use Decimal arithmetic and currency-specific rounding at defined calculation boundaries. A project chooses its comparison currency; no currency, rate, unit conversion, address or missing price is invented. Validate actual currency codes and IANA timezones in the future service; regex/string checks alone cannot do that.

Each source snapshot has immutable content hashes and precise locators: spreadsheet + tab + bounded range + stable row identity; Gmail message/thread; document page/section; exact Calendar event. Preserve approved snapshot revisions. Changed requirements or contacts invalidate affected RFQ/quote/award/action assumptions before further writes.

## Entities

| Record type | Required content and relationships |
| --- | --- |
| `project` | Context, simulation flag, quote/delivery deadlines and timezone, comparison currency, required/resolved/excluded item scope, scope approvals, unresolved issues, owned spreadsheets/events and cleanup state. |
| `boq_item` | Section/group, description, positive quantity/unit, specifications, delivery requirements and source evidence. Never silently fill missing quantities/specifications. |
| `vendor` | Supplied vendor identity, verified contact evidence, email and supported categories. Search results cannot become approved recipients without contact review. |
| `rfq` | One vendor/contact, explicit item scope and quantity/specification snapshot digest, RFQ revision, quote deadline/currency, reference, sent message and all reviewed conversation threads. |
| `quotation` | Exact RFQ revision/scope/vendor, source message/thread and received time, itemized quantity/rate/line totals, currency, discount/tax/freight/other charges/grand total, delivery/validity dates and compliance evidence state. |
| `award` | Selected quotation revision and item scope, vendor, total, rationale, selection type, exact human approval reference and sent message. A single offer is not a competitive best-price result. |
| `purchase_order` | Stable PO number, approved award/vendor, immutable item/price/specification snapshot, totals and terms, release approval, contact threads, cumulative line quantities, tracking, buyer confirmations, exceptions and optional hold-resume state. |
| `fulfilment_event` | Exact PO, stage, actor role and authority state, provider/message identity, deduplication key, observed/explicit occurrence timestamps, line quantities and evidence. Do not infer physical dates from mailbox arrival. |
| `approval` | Purpose, trusted human identity/roles, decision and expiry, exact workflow/version/action/policy revision, operation, destination/recipient references, action digest and canonical approval reference. |
| `evidence` | Source kind/provider/identity/locator, content hash/time, authority classification, asserted role and independently verified subject where available. Model analysis and source accessibility are not proof of the claim. |

Incomplete extraction is represented explicitly with null unknown fields and NEEDS_CLARIFICATION. ACTIVE projects, READY/ORDERED BOQ items and QUALIFYING quotes require complete fields; preliminary facts are never fabricated just to satisfy the schema. Unmatched messages remain quarantined evidence until RFQ/vendor identity is resolved.

`examples.json` contains fictional **representation fixtures**, not live approvals or provider evidence. The demonstration project is a simulation and its compliance/source evidence is labelled accordingly.

## Financial and scope invariants

The future service must check these before `QUALIFYING` or award selection:

1. Each quoted item belongs to the exact RFQ scope and revision; item IDs are unique and quantity/unit/specification coverage matches. Partial offers are flagged; comparison can use an explicitly approved split scope, never incompatible bundles.
2. `line_total = quantity × unit_price`; `subtotal = sum(line_total)`; `total = subtotal - discount + tax + shipping + other_charges`, after explicit currency rounding. Record the tax/discount basis and any included/excluded costs as source evidence; unknown charge treatment stops comparison.
3. Compare identical approved scopes in one currency. Foreign currency needs explicit reviewed conversion evidence/rate/date in a later contract revision; v1 stops instead of converting. Never mix group totals with per-item prices or double-count freight/tax.
4. Delivery meets the project deadline; quote validity has not expired in the project timezone; required compliance is independently verified. A supplier saying YES is a claim until required evidence is checked. `SIMULATION_ONLY` may qualify only for a simulation project.
5. Wait for the requested quotation set or reviewed deadline/early-close decision. Missing offers and single-offer groups require visible exception review; ties require a documented decision rather than arbitrary selection.

## Evidence, identity and correlation

Use known thread + RFQ/PO reference + reviewed sender/contact + current scope as corroborating signals. When a reply moves to another thread, an exact reference alone is insufficient: verify sender, scope and related conversation before adding that thread. Conflicting/multiple references stop the affected case. An RFQ request, award message or quoted old email is not a new quotation/update. Ignore quoted history as fresh evidence; duplicates must not cause a second comparison, send or state transition.

Production buyer/supplier roles come from trusted authenticated subjects and reviewed contacts, not an email body stating `Role: Buyer`. The one-account pilot can only provide `SIMULATION_ONLY` role evidence; it cannot establish independent supplier/buyer identity or authorize real procurement.

## Ownership and persistence boundary

SQLite tables, foreign keys and unique indexes are next-step implementation, not created here. Planned uniqueness includes workspace/project/record/revision, provider mailbox/message, RFQ vendor/scope/revision, PO number and action/effect ID. Commit an evidence-backed state revision and its outgoing sync intents transactionally. Gmail/Sheets/Calendar are separate systems; there is no distributed transaction. Use per-target sync status and reconciliation, not a claim of atomic provider updates.

Schema validates representation and a few local closure/approval conditions. Cross-record arithmetic, signatures, chronology, evidence authority, revision matching, resource ownership and state transitions require the later service and cannot be guaranteed by JSON Schema alone.
