# Subway ontology and workflow evidence coverage audit

Current scope follows [dump-grounded revision 4](subway-dump-grounded-ontology.md).
This document describes historical enrichment/audit work. Its unconnected classes
are excluded from new planning; historical immutable versions remain available.


Audit date: 6 November 2026. The previous enrichment was a selected evidence model,
not complete application coverage. This audit found missing business-model definitions,
missing workflow read bindings and rule-only retrieval failures, then corrected them.
It does not certify that every future business question is answerable.

## Audited version

`bov_subway_audited_v3` / package `subway-business-v1` revision 3:

| Coverage | Previous revision 2 | Audited revision 3 |
| --- | ---: | ---: |
| Concepts | 89 | 158 |
| Relationships | 91 | 156 |
| Reviewed descriptive rules | 28 | 28 |
| Modules | 15 | 26 |
| Supplied business models represented | 58 selected model files | 156 declared business models |
| Restored collections with workflow reads | 12 | 52 |
| Workflow field mappings | Selected scalar fields | 637 explicit projections |

All 52 restored collection concepts remain. The other 104 concepts are code-only
business models; two additional concepts express the existing modelling conventions.
Code-only definitions are useful for explanations but cannot supply company records.
Original archives, earlier immutable versions and earlier workflow pins are preserved.

## Complete source inventory

The audit statically scanned all 527 JavaScript model/service files from the eight
archives: 156 business-model files, 63 infrastructure/security files, 10 schema/helper
files and 298 service files. No supplied application code was executed. The inventory
records file hashes, model declarations, typed fields, scalar/array reference declarations
and explicit throw-site locations/hashes. Getter-only `mongoose.model(name)` calls and
comments are not model declarations. This is a static source inventory, not proof that
all possible runtime branches or dynamically constructed models have been discovered.

| Application | Business-model files represented | Service files inventoried | Files contributing reviewed rules |
| --- | ---: | ---: | ---: |
| Finance | 36 | 117 | 8 |
| Intranet | 24 | 40 | 1 |
| CF approvals | 20 | 31 | 1 |
| Document storage | 8 | 14 | 1 |
| Invoice tracking | 16 | 24 | 1 |
| Quality/QNet | 8 | 16 | 1 |
| Franchise/SUBS | 32 | 30 | 2 |
| Technical/TechNet | 12 | 26 | 2 |

Authentication, credentials, tokens, raw logging and identity infrastructure are
accounted for separately rather than imported as business data. References are resolved
only to exact, unambiguous declared models in the same application. All 111 unresolved
references are recorded: 95 target User, 13 Person, and three target the unmatched
names SmallWareItem, vendor and Waiver. Similar spelling does not authorize merging
identities or executing joins. No new data credentials or write permissions were created.

## Corrections to workflow evidence access

Revision 3 adds an explicit read for every restored collection, including previously
unavailable document, approval configuration, category, smallware, report and vendor
mapping records. Role-qualified capability identifiers avoid cross-database collisions.
All existing revision 1/2 projections remain exactly pinned and supported by their
original providers. Providers accept only a complete binding from a verified immutable
package; changes to collection, fields, limit, owner or byte budget are rejected.

Report columns such as `Invoice Amount` were previously rejected by an identifier-only
name check. The new operator-pinned projections allow spaces in MongoDB field labels,
retain the original field names, and preserve secret/operator-character restrictions.
General source browsing and older packages retain their existing name validation.

Reads return up to 25 complete rows in native identity order, with fewer rows when
needed to stay inside the existing 100 KB evidence limit. Returned coverage explicitly
states `complete_dataset=false` and limits conclusions to the projected sample. A
single oversized record fails explicitly rather than being silently truncated. The
existing per-record 64 KB and source-query 2 MB limits also remain.

`central.blogprojects` is empty and has no sampled field schema. Its binding permits
only a one-row existence probe through the native identity index. It returns no invented
records and fails closed if records appear or metadata changes, requiring schema review.

The larger 249,345-byte catalog is provisioned with a trusted 300 KB operator allowance;
request JSON cannot increase the ordinary 100 KB package publication allowance.
Catalog validation supports 128 available capabilities; an individual workflow still
permits at most 16 action tasks. Existing execution contracts and evidence limits remain.

## Retrieval and planning verification

Previously, module selection used module and concept labels, so a question about
`initialApproval` could select approval modules while omitting the actual procurement
rule. `allowConfirm` and Saturday/Sunday questions could return no match at all.
Subway retrieval now ranks saved rule conditions/outcomes, field declarations and exact
code quotations, while keeping the existing reference/character bounds and owner/version
checks. Other clients retain their previous retrieval behavior.

Five representative identifier/condition questions find the expected cited rules.
All 156 business-model definitions and all 28 saved rules were retrievable by their
saved names (184 lookups). This verifies discoverability, not live-model response quality
or correctness for arbitrary phrasing. Planning also receives explicit connected versus
code-only coverage and the unsupported package operations.

All 76 old/new read capabilities were exercised against the actual restored database:
12 in revision 1, 12 in revision 2 and 52 in revision 3. A staged controlled-planner
workflow completed through existing preparation, Registry and runtime using revision 3.
No external model calls, outgoing actions or source writes were performed.

## Limits that can still produce a legitimate evidence gap

- The supplied dumps restore central/finance data. The 104 code-only classes have no
  matching connected records. Application code cannot reconstruct those missing records.
- The 28 rules describe selected reviewed guards. The full static inventory found 960
  throw sites across the service files (991 across all inventoried files); many are
  technical errors or overlapping checks. They have not all been interpreted as business
  rules. No exhaustive business-policy certification is claimed.
- Source schema properties are bounded sampled scalar projections, not every nested,
  array, binary, sensitive or possible production field. 637 mappings do not establish
  complete field coverage or authoritative calculation semantics.
- Package reads do not execute arbitrary filters, exhaustive totals, aggregates, automatic
  joins or archived applications' approval/payment/credit actions. Relevant definitions
  cannot substitute for an executable query or business action adapter.
- Restored snapshots do not establish current production state. Empty, absent, conflicting
  or oversized records, source changes, unverified policies and defective source guards
  still need an accurate explanation rather than a fabricated answer.

These limits are distinct from the avoidable missing definitions, missing read bindings
and failed retrieval corrected in this audit. A response requiring one of these limits
should identify the exact missing dataset, field, operation or policy.

## Evidence and validation

Public immutable artifacts are under `ontology/subway/`: `business-ontology-v3.json`,
`knowledge-package-v3.json`, `coverage-inventory-v3.json`, `validation-report-v3.json`.
Full verification and deployment records are in
`openspec/changes/subway-ontology-coverage-audit/verification.md`.
Private read/count/retrieval receipts, staging store, logs and deployment backup are
under `.local/tenants/subway/coverage-audit/`. Original ZIPs and database archives were
not changed. Live chat remains the user's own test, as previously requested.
