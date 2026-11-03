# Simpson Business Ontology

Status: the separate Business Ontology tab is live with source-cited definitions, saved source graphs, reports, three fixed business-rule handlers and warranty assessments. Workflow creation now automatically consults relevant saved business knowledge and shows step-level evidence. See [workflow planning and how to test it](workflow-planning.md), [foundation API and UI](foundation-api.md), [extraction and draft versions](extraction-api.md), and [OWL/RDF and SHACL compilation](compiler-api.md). Historical chunk notes below retain their original scope.

**Live functional rollout (1 November 2026):** the Business Ontology tab is now active in the existing shared-workspace application. See [access, backup/recovery and live verification](functional-rollout.md). Individual login remains deferred as requested; historical local-only notes below describe earlier chunks.

This is the separate business ontology requested by the owner. The existing Data Intelligence → Ontology tab and its ontology-foundation artifacts remain independent. Uses the existing OpenAI integration; no Bedrock dependency and no SME ontology validation interface or approval gate. Operational warranty, replacement and quality approvals remain business concepts.

## Evidence and scope

Both current scoped Simpson MongoDB connections were successfully read through the existing connector. The final [aggregate report](source-verification-2026-10-31-v2.json) covers 13 db1 and eight db2 collections. Nineteen returned records and two returned none. Each profile examines at most the first 100 unsorted records, with a three-second server operation limit. These are point-in-time observations, not random samples or population totals.

Only field/type/missing/null counts and direct-reference outcome counts were exported. No source records, identifiers, credentials or field values were exported. No company writes, ontology mutations, model calls, workflows or application services were invoked. Current connector configuration compared unchanged before and after each run.

- [Source basis](source-basis.json): supplied archive/blueprint hashes, reviewed reference-repository revision, and ten code findings with file hashes and line references. Code was inspected, not executed; correspondence to the deployed Simpson backend is not asserted.
- [Mapping inventory](mapping-inventory.json): 21 proposed concept-to-source mappings with exact field names and observed types.
- [First probe](source-verification-2026-10-31.json): preserved initial evidence. The final v2 probe corrects the diagnostic's product/stock field selection against supplied source and saved metadata: products use `listData`; stock uses `serialNumber` and `status`. These are field-selection corrections, not changes to source data.

## Both database boundaries

| Source | Coverage |
| --- | --- |
| db1 | OEM companies/accounts, engine invoices, tickets, inspections, engine/part replacements, dispatch, FOC, inward records, internal cut-ins, bulletins, service information |
| db2 | Manual claims, SAP claims, failed-engine/part analysis, ICA/CAPA, products, SAP float stock, inspection operation logs |

Both databases are inputs to the new ontology. Cross-database links remain candidates until their scope and identifiers are verified. A serial match alone is not resolved physical-engine identity. Claims and QA records do not declare direct ticket references in the supplied models. Existing source-backed ontology relationships are not silently imported as business facts.

## Live findings

| Observation | Consequence |
| --- | --- |
| 100/100 sampled tickets linked to an OEM account and 100/100 to an OEM company | These direct references support the initial case mapping within the sample. |
| 100/100 inspection ticket links, 97/97 dispatch ticket links, and 100/100 FOC ticket links resolved | Use these explicit relationships; do not imply global reference integrity. |
| 98/100 engine-replacement ticket links resolved; two did not | Non-blocking data-quality gap. Preserve the two unlinked records and continue with resolved relationships; do not guess ticket IDs. Owner explicitly accepted proceeding. |
| Nine of 100 sampled complaint sale dates were null | Warranty evaluation needs a missing-information outcome. |
| Complaint HMR was string-valued; ticket HMR was numeric | Explicit numeric parsing and invalid-value handling are required. Type observation alone does not validate the stored contents. |
| Replacement status, assigned approver and cut-in number were missing in the first 100 tickets | Not observed in this bounded sample, not proof of schema absence. Prior targeted field evidence is retained independently. |
| Six manual claim records and 100 SAP claim records were sampled | Keep manual and SAP claim lines separate; no deduplication or ticket association is established. |
| SAP invoice date/status and several newer claim fields were missing in this SAP sample | Do not assume the supplied model's fields are populated in historical records. |
| Eight failed-engine analyses were sampled; three lacked cut-in effective date | Code-backed QA concepts have live data, but effectivity dates can be incomplete. |
| Failed-part analysis and ICA/CAPA returned no records | Model declarations support candidate structure, not historical-instance evidence. |
| Product list data is nested; stock serial is `serialNumber` | Keep exact field paths; avoid inventing aliases across collections. |

Counts below 100 are bounded query results, not separately verified population counts. Direct references establish target existence, not whether the association is semantically correct or currently authorized for a future application user.

## Rule sources and gaps

The supplied warranty implementation hardcodes OEM-dependent invoice-month, sale-month and HMR thresholds. It uses inclusive comparisons, calendar year/month differences ignoring day of month, and the current date when evaluated. Earlier code-review notes describing ticket-creation-time evaluation are superseded for this supplied archive: creation calls the function, but later rechecks use the later current date. Future historical reconstruction requires an explicit evaluation timestamp and versioned policy.

Its primary hour input is `tickets.complaintRecord.hmr`, and its sale input is `tickets.complaintRecord.dateOfSale`. The engine invoice lookup uses serial alone despite the source model's company+serial uniqueness declaration. It rejects zero HMR via truthiness, has incomplete invalid-date checking, and can return null or throw for incomplete input. These are observed implementation behaviors, not desired rules to reproduce unquestioningly.

No complete coverage/exclusion evaluation or versioned warranty policy source was identified. Existing `underWarranty` booleans do not supply missing policy. A future eligibility rule must return Requires Review where required policy/input evidence is insufficient.

Inspection publication includes core system checklists, conditional UC06/UC07/SJV requirements, assigned-engineer checks and defect-code requirements. Replacement and QA approvals remain separate from warranty eligibility. Out-of-warranty technical support may continue.

Current cut-in lookup does not fully constrain OEM/plant/list/approval applicability and compares strings. A stored POST_CUT_IN label is not confirmed recurrence. The new ontology must distinguish applicability, incorporation, comparable failure mechanism, and operating exposure. No complete exposure-denominator or engineering-change incorporation evidence was established by this chunk.

## Chunk handoff

Chunk 3 is implemented and verified locally: scoped evidence documents, explicit OpenAI generation jobs, source-cited draft definitions and immutable version browsing. The single approved real-provider warranty test returned 14 concepts, seven relationships and two non-executable candidate rules. See [extraction and draft versions](extraction-api.md). Chunk 4 adds deterministic OWL/RDF and SHACL compilation, structural validation reports and version-bound downloads; see [compiler API and limits](compiler-api.md). The real warranty draft passed offline compilation with 31 retained information/mapping warnings. Chunk 5 adds an evidence-backed candidate-rule catalogue, six read-only definition queries and the 22 blueprint business questions with their missing-data prerequisites; see [rule catalogue and queries](rules-and-queries.md). Chunk 6 adds explicit mappings, bounded source graphs, typed references/candidate matches and instance-shape validation using both sources; see [source graph scope and API](source-graph.md). The real QA-anchored check retained an invoice from db1 and a failed-engine analysis from db2 as separate records with a candidate serial edge. Monitoring still requires incorporation, confirmed comparable failures and exposure evidence. Chunk 7 adds curated drafts for missing modules, selected-version module/evidence/gap coverage and six provenance-backed reports over saved graphs; see [reference modules and intelligence](reference-and-intelligence.md). Draft coverage is distinct from verified policy or populated business instances. Chunk 8 adds explicit [warranty input readiness](warranty-readiness.md) for a selected saved complaint, preserving missing policy/identity/time-basis requirements as Requires Review with eligibility not evaluated. Chunk 9 adds [source-cited policy draft revisions and saved-case scope/date comparisons](policy-drafts.md), with explicit time/invoice selection and non-executed limits/exclusions. No real policy is seeded, and matching observations do not verify applicability. Chunk 10 adds [typed record-reference and candidate association checks](engine-associations.md), correcting the supplied model's OEM account/company distinction and preserving native identifier evidence in new graphs. Older snapshots remain readable with explicit type uncertainty; no physical identity is invented. Chunk 11 adds [deterministic warranty assessment](warranty-assessment.md), explicit cited calculation conventions and a saved-case action with check explanations and exports. Missing/unverified policy, identity or exclusion findings retain Requires Review; draft arithmetic never establishes approval or denial. Authoritative policy/applicability, physical-engine/crosswalk and exclusion evidence remain prerequisites for final eligibility. Chunk 12 adds [monitoring evidence readiness](monitoring-readiness.md): explicit date-window/change inspection, source observations, prerequisite gaps and bounded exports. Recurrence/rates/effectiveness remain unavailable without verified incorporation, comparable failures, cohorts and longitudinal exposure. Chunk 13 provides an [offline release audit, all 22 acceptance gaps and private artifact recovery/deployment runbook](release-preparation.md). Current backend production mode refuses startup until trusted production login is implemented; passing artifact checks does not accept business competencies or authorize deployment. Preserve old ontology state, shared contracts and current connections. Subsequent extraction and mapping must retain the code/database/blueprint evidence distinctions above. All twelve modules remain in the eventual scope; sparse modules can start with definitions and explicit missing-data states.

Verification: 13 focused tests passed, including the new aggregate-only probe tests and existing targeted field-verification tests. Strict OpenSpec validation of `simpson-business-ontology` passed. Live queries succeeded on both sources; no company mutations occurred.


The three displayed reference safeguards now have complete [rule execution, cited input revisions, explanations and exports](rule-execution.md). This adds a working evaluation path for documented root-cause findings, post-change recurrence conditions and explicitly defined cohort rates. Missing company evidence remains visible; it is not replaced by fabricated diagnoses, thresholds or denominators.
