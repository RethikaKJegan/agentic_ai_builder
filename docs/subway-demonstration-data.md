# Persistent Subway demonstration data

In the existing Subway Overview, start a request with:

> Use Subway demonstration dataset v1. Investigate purchase orders against invoices, receipts, approvals and budgets under the modeled policy and prepare an evidence-backed report.

The prefix is an explicit dataset selection. It works with the existing workflow review, approval, query, investigation, report and automation interfaces. Requests without it retain the historical Subway source context. A saved workflow pins the selected dataset, ontology, policy and immutable source fingerprint. There is no source import or operational write.

The application persists 192 generated records across 18 collections in the Subway SQLite store: stores, vendors, finance locations and explicit mappings; purchase requisitions and orders; approval cycles and stage history; budgets, budget lines, reservations and allocations; receipts; invoice headers and items; and payments. Source metadata, scalar relationship filtering and RAG policy passages use the selected ontology. Existing `subway_query`, `subway_assess` and `subway_documents` tools read this stored source through the normal planner, Registry and runtime.

This is **modeled demonstration data and illustrative policy**, not actual Subway operations or official company rules. The modeled as-of date is 12 November 2026. Nine additional typed rules run in the existing deterministic rule engine alongside structural procurement checks: invoice tolerance (5 currency units), quantities, payments, overdue balances, approval prerequisites (two stages above 5000), budget balances, store and supplier mappings, and bidirectional requisition/order references. Monetary totals must remain separated by currency; there is no exchange-rate conversion.

The eight orders include clean, invoice discrepancy, low available allocation, pending/rejected approval, partial receipt, and missing approval-stage cases. Failing checks and missing evidence are expected findings. Readiness describes whether prerequisites for that particular assessment were supported; it is not a global authorization to buy or pay. Invoice item rows repeat their embedded invoice-header items as separate queryable records; do not add both representations together. Header measures must be aggregated at their native collection grain.

To schedule a demo investigation, use the same prefix and an explicit recurrence, for example:

> Use Subway demonstration dataset v1. Every day at 9 AM India time, reconcile the demonstration purchase orders and prepare a report under the modeled policy. No external delivery.

Review and approve the existing workflow, then activate its proposed schedule. Recurring assessments pin the dataset/catalogue, exact assessment kind, modeled as-of date, delay policy and normal bounded query schema. Dynamic queries remain subject to tenant ownership, source identity, date bounds and the reviewed catalogue. Historical assessments retain exact-input recurring consent. This dataset is a fixed demonstration snapshot; a recurring report does not make it current operational evidence.

Provisioning is opt-in through `BUILDER_SUBWAY_DEMO_ENABLED=1` on the dedicated Subway service. Startup seeds immutable, tenant-scoped `subway_demo_datasets` and `subway_demo_records` tables and an explicitly selected ontology version (`bov_subway_demonstration_v1`, revision 0). Revision 0 keeps the historical ontology as the default. Startup is idempotent and rejects version/hash conflicts. The demo source validates persisted record hashes before reads and never exposes production source credentials. Historical MongoDB records, real source connections, Google integrations and existing schedules are not imported into this dataset.
