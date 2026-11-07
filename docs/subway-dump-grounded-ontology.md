# Subway ontology grounded in the supplied database dumps

Current query path: [complete Subway data evidence](subway-full-data-evidence.md).
New workflows use full relevant data for filters and aggregates. The 25-row package
readers discussed below remain historical inspection tools, outside the default new
query selection. The app-property numeric/string link is now resolved from its schema.


The active scope is the two supplied central/finance database dumps. Application
code explains the records actually present in those dumps. An application model
without corresponding supplied data is not an active ontology class or planning input.

## Revision 4

Ontology `bov_subway_dump_v4`, package `subway-business-v1` revision 4:

- 52 restored collection concepts and two existing modelling parents: 54 concepts.
- 67 relationships between supplied collection concepts, with exact field paths,
  code/schema citations and bounded actual-record checks.
- 13 descriptive code-derived rules relevant to the supplied collections, across nine modules.
- All 52 collection readers and 637 explicit scalar field mappings remain available.

The 104 code-only model classes introduced by the earlier audit are excluded from
this active version. Rules belonging only to unrelated applications are excluded. Two guards relevant to
purchase orders and budget lines retain explicit task-local prerequisites for absent
purchase-request/budget-reservation records, without creating those ontology classes. Earlier immutable versions and packages remain
available for workflows explicitly pinned to them; no historical definitions or
source archives were deleted or rewritten.

## Collection-to-code correspondence

Every restored collection has a matching declared source model. Forty-eight have
matching direct service calls, constructor calls or property references using the
actual model/export symbols. Each mapping records the original ZIP/member hash,
model declaration, export alias, relevant service member and matched line numbers.
A short service-use quotation is attached to the concept where available. Service
usage is static evidence of correspondence, not proof of every branch's behavior.

Four models have no direct service usage in the supplied code: central.plaops,
central.pluems, central.appproperties and finance.reportfiles. The supplied services
import PlAop, PlUem and ReportFile but do not directly call those symbols; unrelated
UserProperties is not treated as AppProperties. These four still have grounded dump
schema/model mappings. Their missing direct service usage is recorded explicitly.

Exact correspondence: `ontology/subway/dump-code-correspondence-v4.json`.
The table below identifies the corresponding model and number of service files.

| Supplied collection | Declared model | Service files |
| --- | --- | ---: |
| central.departments | Department | 4 |
| central.departmentroles | DepartmentRole | 1 |
| central.roles | Role | 5 |
| central.userroles | UserRole | 6 |
| central.stategsts | StateGst | 1 |
| central.vendors | Vendor | 1 |
| finance.companies | Company | 4 |
| finance.locations | Location | 18 |
| finance.foreigncurrencies | ForeignCurrency | 2 |
| finance.vendormappings | Vendormapping | 6 |
| central.stores | Store | 6 |
| central.storeproperties | StoreProperties | 1 |
| central.dcs | Dc | 1 |
| central.electricityconsumptions | ElectricityConsumption | 1 |
| finance.purchaseorders | PurchaseOrder | 15 |
| finance.items | Item | 14 |
| finance.categories | Category | 9 |
| finance.subcategories | SubCategory | 5 |
| finance.faitems | FaItems | 1 |
| finance.budgets | Budget | 8 |
| finance.budgetmodifications | BudgetModification | 2 |
| finance.lineitems | LineItem | 11 |
| finance.grns | Grn | 6 |
| finance.invoicedatas | Invoicedata | 3 |
| finance.vendorgrnstagetimelines | VendorGrnStageTimeLine | 1 |
| finance.approvals | Approval | 14 |
| finance.approvalconfigs | ApprovalConfig | 1 |
| finance.stages | Stage | 3 |
| finance.cfapprovalmappings | CFApprovalMapping | 2 |
| finance.smallwaregrns | SmallwareGrn | 1 |
| finance.smallwareitems | SmallwareItem | 3 |
| finance.smallwarepoconfigs | SmallwarePoConfig | 1 |
| finance.smallwarepos | SmallwarePo | 1 |
| finance.smallwarestages | SmallwareStage | 3 |
| central.arolds | ARold | 1 |
| central.plactuals | PlActual | 1 |
| central.plaops | PlAop | 0 |
| central.pluems | PlUem | 0 |
| central.plreports | PlReport | 1 |
| central.appdocumentcategories | AppDocumentCategory | 1 |
| central.appdocuments | AppDocument | 1 |
| central.appproperties | AppProperties | 0 |
| central.apps | App | 6 |
| central.blogcategories | BlogCategory | 1 |
| central.blogprojects | BlogProject | 1 |
| central.blogs | Blog | 1 |
| central.confirmappdocuments | ConfirmAppDocument | 1 |
| finance.assets | Asset | 1 |
| finance.advancepaymentreports | AdvancePaymentReport | 2 |
| finance.grnreports | GrnReport | 2 |
| finance.poreports | PoReport | 2 |
| finance.reportfiles | ReportFile | 0 |

## Relationship paths and actual-record evidence

Relationship extraction now starts at each mapped model's root schema and resolves
embedded schema variables and arrays. This fixes earlier syntactic paths such as
`stages.type` and `categoryMappings.type.category`; actual document paths are
`stages[]`, `items[].lineItem`, `categoryMappings[].category`, and similar paths.
Unused helper schemas in a file are not presumed to be fields of its exported model.
Only exact same-application ref targets mapped to supplied collections are retained.
The original 11 dump-derived candidate references remain qualified as candidates.

All 67 relationships were checked against actual restored data using up to 200
native-ID-ordered source documents with the path populated, and up to 1,000 scalar
references per relationship. No source records or identifiers are included in the
public probe report, only paths, counts, source/target identities and qualifications.

- 57 relationships matched every sampled scalar reference to a native target ID.
- Two had partial matches: finance.stages.approvalId (189/200) and
  central.apps.properties (4/5).
- Eight had no observed scalar reference values in that bounded check. Their source
  declarations remain valid model intent, not proof of populated edges.

These are 67 saved relationship definitions; overlapping schema/code candidates can
express the same logical link. Counts are not a distinct-join count. Matching samples
do not establish complete referential integrity, approved joins or cross-service
identity equivalence. Array traversal is descriptive evidence, not an installed join.
Exact checks: `ontology/subway/dump-relationship-probes-v4.json`.

All 52 collection counts still match the original restore receipt: 1,218,822 records.
No source writes or supplied-application execution were performed.

## Planning and compatibility

New planning receives revision 4's 54 concepts, relevant relationships/rules and
source citations, with zero code-only concepts in its availability context. It does
not receive unrelated technical-ticket, quality-credit, franchise or CF application
classes/rules merely because their ZIPs were supplied. Missing data is assessed only
against the user's actual requested operation and available collection/field mappings.

The package retains exactly the 52 source bindings and 637 mappings from revision 3.
All four package revisions remain available. Reads are bounded snapshot samples,
at most 25 complete records, possibly fewer for the evidence byte limit. Empty
blogprojects stays explicitly empty and fails closed if records appear without schema
review. Existing current-owner checks, metadata stamps, Mongo collection privileges,
byte limits and exact workflow pins remain in force.

This correction does not create arbitrary filters, exhaustive totals, automatic joins,
write actions or approved business policy. The 13 rules describe the cited implementation
paths; they are non-executable and are not an exhaustive interpretation of all source
services. Original code guard defects and record mismatches remain documented instead
of being normalized into invented policy. A specific missing field, unsupported operation
or absent actual record can still be a legitimate task-local limitation.

Validation/deployment evidence is recorded in
`openspec/changes/subway-dump-grounded-ontology/verification.md`. Private staging,
read/workflow/probe receipts and backups are under
`.local/tenants/subway/dump-grounding/`. No external model calls were made; live chat
remains the user's own test as previously requested.
