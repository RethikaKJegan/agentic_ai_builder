# Subway ontology: source-code relationships and business rules

Current scope follows [dump-grounded revision 4](subway-dump-grounded-ontology.md).
This document describes historical enrichment/audit work. Its unconnected classes
are excluded from new planning; historical immutable versions remain available.


Revision 3 expands this selected enrichment; see the
[coverage audit](subway-ontology-coverage-audit.md) for current counts, all-model
coverage, 52 collection reads and remaining limitations. This document preserves the
revision 2 extraction methodology and reviewed rule catalogue.

The eight supplied application archives were read in place. Selected reviewed code
excerpts were extracted into a new private directory; original archives were neither
modified nor executed. Credentials, application configuration, raw mail and live
application operations were not imported. No external model calls were made.

## Result and authority

Ontology `bov_subway_code_v2` adds 35 concepts, 80 declared model relationships and
28 descriptive implementation rules to the original archive-backed version. The new
version has **89 concepts, 91 relationships, 28 rules, five layers and 15 modules**.

The original 54 concepts and 11 qualified reference candidates remain. Existing
source bindings remain the two read-only central/finance snapshots. The added
concepts explicitly state that corresponding databases are not connected. Same-named
Store, Vendor, Invoice, Department and similar models in different applications remain
separate classes; overlapping numeric IDs are not merged across services.

All new rules describe the supplied application's code paths, including exceptions
and helper dependencies. They are not independently approved policy and have
`executable=false`. No new action handler, approval permission, database join,
source credential or write authority was created. The shared scalar-comparison
package evaluator is deliberately not used to execute application-code rules.

## Evidence coverage

| Archive/application | Evidence represented |
| --- | --- |
| `subway-finance-api-v2-gowtham-finance-v2-pr.zip` | PO/company/location/approval, requisitions, budgets, reservations, allocations, receipts and invoice references; approval guards and conversion checks |
| `subway-intranet-api-master.zip` | Store/application/document/department model references; document confirmation and confirmation reset behavior |
| `subway-cf-approval-api-master.zip` | CF workflow, step configuration, exceptions, financial and capex records; configured input validation and step-authority checks |
| `subway-docustorage-api-master.zip` | Restaurant/document/timeline/company-document models; duplicate upload, edit access and paired-record consistency |
| `subway-invoice-tracking-api-master.zip` | Separate invoice/vendor/voucher/legal-document/stage models; vendor/invoice-number duplicate checks and resubmission routing |
| `subway-qnet-api-master.zip` | Quality complaint/product/category/store references; credit issuance, credit information and closure checks |
| `subway-subs-api-v2-master.zip` | Franchise/store/lease/transfer/waiver relationships; buyer-owner exclusion and compound store lookup for waiver assignment |
| `subway-technet-api-master.zip` | Technical tickets/categories/departments/stores/complaint/escalation models; weekend/hold/expiry selection and configured next SLA level |

Every cited excerpt records archive SHA-256, member SHA-256, member path, line range
and excerpt hash in `ontology/subway/code-evidence-manifest-v2.json`. The ontology
contains exact source quotations and hashed source documents. A TypeScript AST
reader extracts actual `ref` property declarations, excluding commented-out code.
Only explicitly identified model targets in the same service namespace are linked.
This is a scoped evidence model, not a claim to exhaustively model every route/helper.

## Important code qualifications

- PO creation rejects a budget only when `initialApproval` is falsy **and** status
  is not APPROVED. The ontology preserves that bypass rather than asserting an
  unconditional approved-budget requirement.
- The finance GRN duplicate guard compares financialyear, invoiceNumber and
  vendorCode, excluding CANCELLED/REJECTED records. This is an application query,
  not proof of a unique database constraint or concurrency-safe enforcement.
- The advance-invoice positivity guard first tests amount truthiness, so numeric
  zero bypasses that particular guard. An unconditional positive-amount rule was
  not added. The separate maximum-advance comparison is represented as written.
- The smallware GRN approver guard uses `!stage.approverRole === role` and references
  an unresolved `approver.status` in its error path. Effective approver enforcement
  is not asserted; this is recorded as a source defect.
- CF step approval calls a helper that explicitly permits ADMIN and CF_READ_ONLY.
  This questionable read-only-role bypass is described and flagged for clarification,
  not silently converted into an approved authorization policy.
- Intranet document updates reset **all** confirmations matching appDocumentId when
  allowConfirm is enabled. Role/department filters shown earlier select notification
  recipients, not the reset target.
- The QNet store-credit confirmation closure check is commented out. It is not
  represented as enforced. Prior administrator closure and active role checks are
  described from the active branch.
- Store transfer creation looks up storeNo alone; waiver assignment looks up storeNo,
  sequenceNo and satelliteNo. These identities are not treated as interchangeable.
- Technical SLA durations are configuration-driven; the ontology does not invent
  a fixed duration or assert that an escalation email was delivered.

## Platform behavior and compatibility

The existing ontology workspace presents the added modules, relationships, rule
catalogue, source quotations and provenance. Subway module coverage and competency
questions now use its own saved definitions; Simpsons reference content is not
returned for Subway. The specialized engine/warranty graph and policy controls are
kept in the Simpsons workspace. Subway relationship definitions remain inspectable
and exportable in the generic definition and OWL/RDF interfaces.

The server selects package `subway-business-v1`, **revision 2**, for new Subway
planning requests. It pins the new ontology and exposes its concepts and relationships;
matched descriptive rules/citations enter planning through the existing version-bound
ontology evidence retrieval. This gives the planner business context, not additional
execution permissions. No new live data capabilities were invented for the code-only
applications. The same 12 bounded source-read capabilities remain available.

Package revision 1, ontology version 1 and all their previous bindings are retained.
Old workflows keep their existing pins. New rules are not copied into package
comparison rules, which would imply executable semantics.

Deployment appends the new version, compilation, evidence documents and package in
one transaction with a reviewed-baseline check. It does not replace the application
database, restore over source data or import isolated smoke-test workflows.

## Validation and reproducibility

`scripts/build_subway_code_ontology.py` creates a new private evidence directory and
refuses to overwrite it. `scripts/prepare_subway_code_ontology.py` stages a copied
application store. `scripts/install_subway_code_ontology.py` appends reviewed artifacts
to the dedicated Subway store after a backup and baseline check. Original archives
are fingerprinted again before deployment.

Offline validation covers definition schema, exact citations, identifier/reference
consistency, evidence hashes, RDF syntax, SHACL shapes and definition constraints.
Instance conformance, OWL reasoning, deployed source-version equivalence and approved
business-policy verification remain explicitly unclaimed. See the OpenSpec change
verification for tests, source reads, controlled workflow and public UI evidence.

## Rule catalogue

All entries below are descriptive and non-executable. Exact quoted code is saved
with each definition; the listed provenance locates the primary excerpt.

### Procurement and catalogue

**Linked requisition must be approved before purchase order creation** (`procurement:code_rule_approved_pr`). The creation request supplies purchaseRequestId. Require an existing APPROVED requisition, successful conversion permission check and delivery/item/rate-contract validation. Helper implementations determine their exact conditions.

Source: `subway-finance-api-v2-gowtham-finance-v2-pr.zip` → `subway-finance-api-v2-gowtham-finance-v2-pr/src/services/purchase-order-service/create-po-core.service.js`, lines 41–54.

**Independent purchase order requires department** (`procurement:code_rule_independent_department`). No linked purchaseRequestId is supplied. body.department is absent or falsy. Reject creation with Department is required.

Source: `subway-finance-api-v2-gowtham-finance-v2-pr.zip` → `subway-finance-api-v2-gowtham-finance-v2-pr/src/services/purchase-order-service/create-po-core.service.js`, lines 55–58.

**Purchase order budget approval guard** (`procurement:code_rule_budget_approval`). The resolved budget.initialApproval is falsy. The budget.status is not APPROVED. Reject purchase order creation. A truthy initialApproval bypasses this particular guard; this is not an unconditional approved-budget rule.

Source: `subway-finance-api-v2-gowtham-finance-v2-pr.zip` → `subway-finance-api-v2-gowtham-finance-v2-pr/src/services/purchase-order-service/create-po-core.service.js`, lines 73–76.

**Ticket metadata for ticket-required line-item category** (`procurement:code_rule_ticket_category`). The line-item category has isTicketRequired. The item lacks ticketNumber or ticketCreationDate. Reject item validation. This does not establish a validated foreign key to the technical-ticket service.

Source: `subway-finance-api-v2-gowtham-finance-v2-pr.zip` → `subway-finance-api-v2-gowtham-finance-v2-pr/src/services/line-item-service/po-line-item-check.js`, lines 45–64.

**Requisition item short close requires creator and allowed state** (`procurement:code_rule_creator_short_close`). A user requests item short close. Reject a user whose normalized ID differs from createdBy; allow this guard only for APPROVED or CONVERTED requisitions. Other short-close checks still apply.

Source: `subway-finance-api-v2-gowtham-finance-v2-pr.zip` → `subway-finance-api-v2-gowtham-finance-v2-pr/src/services/purchase-request-service/short-close.service.js`, lines 21–29.

### Budgets and allocation

**Budget reservation requires available line-item amount** (`budgets:code_rule_reservation_available`). Aggregated reservation amount for a line item exceeds its availableAmount, with missing availableAmount treated as zero. Reject within the transaction. Otherwise the shown path decrements availableAmount and creates an active reservation; no concurrency proof is claimed.

Source: `subway-finance-api-v2-gowtham-finance-v2-pr.zip` → `subway-finance-api-v2-gowtham-finance-v2-pr/src/services/budget-reservation.service.js`, lines 25–65.

**Budget modification rejects nonpositive updated price** (`budgets:code_rule_positive_modification`). updatedPrice is less than or equal to zero. Reject this modification. The excerpt also special-cases oldPrice zero in percentDiff calculation.

Source: `subway-finance-api-v2-gowtham-finance-v2-pr.zip` → `subway-finance-api-v2-gowtham-finance-v2-pr/src/services/budget-modification.service.js`, lines 19–27.

### Goods receipts and invoices

**Active goods receipt uniqueness check** (`receipts:code_rule_grn_duplicate`). Another GRN has the same invoiceNumber, vendorCode and financialyear. That GRN status is neither CANCELLED nor REJECTED. Reject GRN creation. This application lookup is not proof of a unique database constraint or concurrency-safe duplicate prevention.

Source: `subway-finance-api-v2-gowtham-finance-v2-pr.zip` → `subway-finance-api-v2-gowtham-finance-v2-pr/src/services/grn-service/index.js`, lines 26–41.

**Advance invoice update amount ceiling** (`receipts:code_rule_advance_maximum`). The stored invoice type is ADVANCE_INVOICE. The incoming invoiceAmount exceeds the populated purchase order advance.advanceAmount. Reject the update. Missing population or values require separate validation; no policy threshold is invented.

Source: `subway-finance-api-v2-gowtham-finance-v2-pr.zip` → `subway-finance-api-v2-gowtham-finance-v2-pr/src/services/invoice-data-service/index.js`, lines 92–103.

### Operational approvals

**Approval configuration update protects pending approvals** (`approvals:code_rule_config_update_pending`). An approval references this configuration with status APPROVAL_IN_PROGRESS. Reject configuration update until those approvals close.

Source: `subway-finance-api-v2-gowtham-finance-v2-pr.zip` → `subway-finance-api-v2-gowtham-finance-v2-pr/src/services/approval-config.service.js`, lines 47–60.

**Approval configuration deletion protects pending approvals** (`approvals:code_rule_config_delete_pending`). An approval references this configuration with status APPROVAL_IN_PROGRESS. Reject configuration deletion.

Source: `subway-finance-api-v2-gowtham-finance-v2-pr.zip` → `subway-finance-api-v2-gowtham-finance-v2-pr/src/services/approval-config.service.js`, lines 99–109.

**Area and regional manager configuration restriction** (`approvals:code_rule_manager_location`). The location type is absent or HO. The configured approver role matches the configured area-manager or regional-manager ID. Reject this approval configuration; resolve role IDs and location types from their authoritative configuration.

Source: `subway-finance-api-v2-gowtham-finance-v2-pr.zip` → `subway-finance-api-v2-gowtham-finance-v2-pr/src/services/approval-config.service.js`, lines 32–44.

### Documents and report evidence

**Document confirmation requires configured department mapping** (`evidence:code_rule_document_department`). The application document configuration lists the user role in deptMappingRoles. Require the user department in the document category departments; reject an existing confirmed user/document pair.

Source: `subway-intranet-api-master.zip` → `subway-intranet-api-master/src/services/app-document.service.js`, lines 74–94.

**Document update resets confirmations when enabled** (`evidence:code_rule_invalidate_confirmations`). The application properties allowConfirm flag is enabled during document update. Set isConfirmed false for all confirmation records matching appDocumentId. Role/department filters in this path select notification recipients, not the reset target.

Source: `subway-intranet-api-master.zip` → `subway-intranet-api-master/src/services/app-document.service.js`, lines 21–55.

### CF approvals and capital planning

**CF step inputs use configured type and requiredness** (`cf_approvals:code_rule_typed_inputs`). A CF step collects inputs against its configured inputFields. Reject missing required values unless skipRequiredCheck applies, invalid configured dropdown choices, missing conditional uploads and numeric values converting to NaN.

Source: `subway-cf-approval-api-master.zip` → `subway-cf-approval-api-master/src/services/cf-v2.service.js`, lines 104–158.

**CF approval enforces current step authority** (`cf_approvals:code_rule_step_approval`). The record is IN_PROGRESS and its current step is 1 or a later configured step. Step 1 resubmission requires the creator; later steps call isAuthorizedForStep. That helper explicitly returns true for ADMIN and CF_READ_ONLY, otherwise checks configured user/regional-user/role matches. The read-only role bypass is a source concern, not an approved authorization policy.

Source: `subway-cf-approval-api-master.zip` → `subway-cf-approval-api-master/src/services/cf-v2.service.js`, lines 1300–1325.

### Restaurant document storage

**Document upload rejects its matching key** (`document_storage:code_rule_duplicate_document`). A document exists for the documentMatchingFilter assembled in this function. Reject duplicate upload; otherwise create document and upload timeline records. Retain the actual matching filter rather than inventing a global document uniqueness key.

Source: `subway-docustorage-api-master.zip` → `subway-docustorage-api-master/src/services/document.service.js`, lines 9–24.

**Document update requires aligned document and timeline** (`document_storage:code_rule_document_timeline`). An update resolves document and timeline using their matching filters. Reject missing records or denied edit access. License updates additionally call removeAppliedFor; its effect requires helper evidence.

Source: `subway-docustorage-api-master.zip` → `subway-docustorage-api-master/src/services/document.service.js`, lines 27–45.

**Document upsert refuses partial document/timeline state** (`document_storage:code_rule_upsert_consistency`). Exactly one of document or matching timeline exists. Reject as out of sync. When neither exists the shown path creates both; existing pairs require editAccess.

Source: `subway-docustorage-api-master.zip` → `subway-docustorage-api-master/src/services/document.service.js`, lines 48–76.

### Invoice tracking and legal documents

**Invoice tracking update checks invoice number and vendor** (`invoice_tracking:code_rule_vendor_invoice_unique`). The update supplies invoiceNumber or vendor. The resolved pair matches another invoice excluding the current ID. Reject update with Duplicate Invoice Number. This is separate from finance InvoiceData and not proof of a database unique index.

Source: `subway-invoice-tracking-api-master.zip` → `subway-invoice-tracking-api-master/src/services/invoice.service.js`, lines 44–59.

**Invoice resubmission resets approval routing** (`invoice_tracking:code_rule_resubmission_routing`). resubmit is truthy. If the incoming invoiceType is in AM_APPROVAL_REQUIRED_INVOICE_TYPES, assign AM and reset shown AM/RM fields; otherwise assign Finance and clear amApprovalRequired. Reset the shown Finance approval fields. The type list is configuration, not an invented threshold.

Source: `subway-invoice-tracking-api-master.zip` → `subway-invoice-tracking-api-master/src/services/invoice.service.js`, lines 62–93.

### Quality complaints and credit handling

**Quality credit issuance uses role and case participant checks** (`quality_cases:code_rule_credit_authority`). The incoming status is CREDIT_ISSUED. Require the shown DC/vegetable-vendor/admin checks, matching vendor/DC identities where applicable, and reject action-taker role. Branch-specific exceptions remain as coded.

Source: `subway-qnet-api-master.zip` → `subway-qnet-api-master/src/services/case.service.js`, lines 148–174.

**Quality case closure requires prior admin closure** (`quality_cases:code_rule_closure_admin`). The incoming status is CLOSED. Require closedByAdminAt and an ADMIN or R&D role. The commented store-credit confirmation guard is not treated as enforced.

Source: `subway-qnet-api-master.zip` → `subway-qnet-api-master/src/services/case.service.js`, lines 252–261.

**Quality credit issuance requires credit information** (`quality_cases:code_rule_credit_information`). The incoming status is CREDIT_ISSUED and creditInfo is absent. Reject as Credit information missing. Status progression is separately checked against nextValidStatuses.

Source: `subway-qnet-api-master.zip` → `subway-qnet-api-master/src/services/case.service.js`, lines 286–322.

### Franchise, lease and store transfer records

**Store transfer rejects an existing buyer owner** (`franchise_records:code_rule_transfer_owner`). The store is found by parsed storeNo. An owner ID equals parsed buyerPersonNum. Reject the transfer; a missing store is also rejected. Sequence/satellite identity is not established by this lookup alone.

Source: `subway-subs-api-v2-master.zip` → `subway-subs-api-v2-master/src/services/store-transfer.service.js`, lines 10–25.

**Waiver assignment requires an existing store** (`franchise_records:code_rule_waiver_store`). The create request supplies a store identifier. Reject if the store lookup returns no store; otherwise create the assignment. This does not prove waiver eligibility or lease compliance.

Source: `subway-subs-api-v2-master.zip` → `subway-subs-api-v2-master/src/services/waiver-assignment.service.js`, lines 9–19.

### Technical tickets and escalation

**SLA escalation selection observes holds and weekends** (`technical_support:code_rule_sla_selection`). The scheduler selects tickets for SLA escalation. Use the shown OPENED/internal-or-external/hold/expiry filters. On Saturday or Sunday in Asia/Kolkata, exclude departments whose holdWeekEndEscalations is true.

Source: `subway-technet-api-master.zip` → `subway-technet-api-master/src/services/ticket.service.js`, lines 208–234.

**Ticket escalation advances only to configured next level** (`technical_support:code_rule_next_sla`). The category has an escalation matrix with a next-level entry. Set the next SLA level and compute expiry from current time plus the first next-level configured sla hours. Do not invent a fixed SLA duration or assert email delivery.

Source: `subway-technet-api-master.zip` → `subway-technet-api-master/src/services/escalation.service.js`, lines 159–181.

