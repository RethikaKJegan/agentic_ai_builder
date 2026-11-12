# Subway procurement knowledge implementation

This change adds `subway-procurement-v1`, a versioned, hash-bound extension of the existing `bov_subway_dump_v4` ontology. It preserves the original immutable ontology and client package, using the existing query planner, typed-condition evaluator, native identity diagnostics, Registry, CrewAI, GraphRunner, adaptive evidence, reports, document retrieval and Knowledge Map. It introduces no alternative workflow engine or UI.

## A. Exact code changes

New files:

- `ontology/subway/procurement-knowledge-v1.json`: reproducible source-cited runtime knowledge extension.
- `ontology/subway/procurement-source-observations-v1.json`: aggregate observations from read-only queries against the restored finance snapshot; contains no generated company records.
- `scripts/build_subway_procurement_knowledge.py`: deterministic offline authoring utility, reading the existing ontology and supplied finance code archive.
- `workflow_api/subway_procurement.py`: pure deterministic assessment using `business_knowledge_model.evaluate_rule` and `associate`.
- `workflow_api/subway_assessments.py`: tenant-bound, read-only Registry connector with bounded source traversal and verified receipts.
- `tests/fixtures/subway_procurement_scenarios.py`: test-only deterministic modeled datasets.
- `tests/test_subway_procurement_knowledge.py` and `tests/test_subway_procurement_runtime.py`: semantics, accounting, isolation and actual platform-runtime acceptance with controlled providers.

Modified files:

- `workflow_api/subway_queries.py`: bounded status discovery and relevant planning semantics; connector installation. Existing QUERY/INPUT contracts remain unchanged.
- `workflow_api/business_planning.py`: source-bound procurement annotations on existing concept references, preserving reference identities.
- `workflow_api/subway_documents.py`: actual source-text retrieval for the extension through the existing RAG/document reader.
- `workflow_api/live_providers.py`: Subway-only Registry registration and quota for `subway_assess`.
- `workflow_api/automation.py`: exact reviewed consent for recurring assessment inputs; existing query and Google contracts remain unchanged.
- `workflow_api/workflow_adaptive.py`: current-authority, persisted-receipt and knowledge-hash verification for assessments; evidence gaps, pagination and historical freshness remain explicit.
- `runtime/action_plans.py`: exact request/scope/version verification for assessment receipts.
- `workflow_api/workflow_knowledge.py`: exact projected-field usage and applied rule/outcome/version descriptions in the existing Knowledge Map.
- `ontology/subway/demo-business-definitions-v1.json`: profile revision 2 corrects the obsolete literal PENDING example to source-defined approval_in_progress.

OpenSpec proposal, requirements, tasks, verification and deployment evidence are under `openspec/changes/subway-procurement-knowledge/`. Unrelated pre-existing checkout changes are excluded from the deployment patch.

The only new application table is the lazily created `subway_assessment_receipts`, keyed by workspace, owner and assessment ID. There are no business-source migrations, source writes, connection replacements, shared contract changes or frontend changes.

## B. Ontology and business semantics

The extension contains 10 native identity definitions, 41 same-source scalar reference definitions, eight source-scoped state models, 11 temporal definitions, 44 reusable typed checks, eight readiness/dependency definitions, and the existing 67 relationship descriptions.

Identity is scoped by connection, collection, native identifier type and native value. Alternative names/codes are candidates only. Duplicate candidates remain ambiguous; missing references remain unresolved. Existing native-reference diagnostics perform comparisons; no physical or cross-system entity merge is authorized.

The source audit enumerated all observed statuses in seven finance collections. It found 390 approval_in_progress approvals. PO records in this snapshot have approved, short_close, rejected, reconsider, cancelled and draft statuses; absence of an approval_in_progress PO status does not justify a PENDING filter. An approval query uses the source-defined parent approval relationship. Source-declared vocabulary and actually observed values are distinguished. Unknown statuses remain unknown; transition arrays remain empty where this implementation has not verified transition prerequisites. Reconsideration is not rejection or approval.

Dates include PO creation/order dates, requisition dates, approval-cycle/stage creation, stage action, invoice/payment dates, receipt inward dates and source financial-year labels. Filtering reuses configured IANA timezones and existing half-open calendar windows. No corporate fiscal calendar, invoice due date or approval completion date is invented. Stage action dates are not silently used as waiting-start dates. Explicit as_of/delay parameters are analytical inputs, not corporate thresholds.

Verified source paths include PO→approval/location/budget; PO line→item/budget line; receipt→PO; invoice→PO/receipt; budget line→budget; and approval→stages. Every production traversal is fixed, bounded and tenant-authorized. Array joins in the general query engine remain prohibited.

Central store↔finance location and central vendor↔PO vendor code equivalence remain unverified. Matching names or integer values do not establish those relationships. Requisition definitions are code-backed, but there is no restored requisition dataset binding.

The extension is saved as a separate versioned artifact rather than rewriting v4 or importing Simpson-specific knowledge schemas. Reviewed compositions retain the extension contents/hash. The assessment connector rejects changed knowledge until reviewed again. The existing OWL/compiler output for the base ontology is preserved; this change does not claim new OWL inference or physical-instance conformance.

## C. Modeled scenario coverage

Sixteen deterministic scenarios generate 226 records in total across their independent datasets (14 records in the standard scenario). They cover standard/multi-stage approval, partial/extra deliveries, duplicate invoices, budget overruns, missing requisition/approval/reservation evidence, approvals in progress, rejection, reconsideration, cancellation, conflicting status history, missing relationships, duplicate PO lines, incompatible currency, invalid amounts and explicit modeled store/location and supplier/code correspondences. Native-identity tests separately cover one-to-one linking, ambiguous duplicates and unrelated namespaces.

Fixtures use stable IDs, source-shaped fields and coherent explicit references except the intentionally broken cases. They validate the normalized analytical record subset; they do not claim full upstream HTTP-write-schema conformance. Invoice currency/full-order scope and budget-line currency in modeled scenarios are supplemental modeled evidence, not fields found in genuine snapshot records.

Production modules never import the scenario generator. The connector accepts an assessment and authorized structured source query, never caller-provided records, policy code, arbitrary traversals or a scenario selector. Pure test evaluations mark every outcome as a scenario and nonauthoritative. No generated records are installed into source collections, live reports or tenant knowledge stores.

## D. Deterministic business reasoning

`subway_assess` evaluates requisition completeness/requester/items/conversion prerequisites; PO headers/vendor fields/amounts/items/currency/reference uniqueness/approval/requisition evidence; invoice references/duplicates/supplier consistency/currency/scope/amount/receipt/approval/item/due-date prerequisites; budget identity/location/period/currency/available/reserved/expenditure evidence; approval state/stage/history/delay evidence; supplier identity limitations; and receipt completeness/line identity/quantities.

Each stable rule has a version, purpose, declared facts, typed conditions, required evidence, related concepts, missing-evidence behavior and provenance. Fact extraction is deterministic; execution reuses `typed_conditions_v1`. Outcomes are PASS, FAIL, INSUFFICIENT_EVIDENCE and NOT_APPLICABLE. Independent rule outcomes remain available even when another prerequisite is missing. Readiness separates required and optional checks and exposes optional gaps; PASS for receipt readiness does not imply invoice reconciliation or official approval.

These are configured analytical checks grounded in source structures and code descriptions, not independently approved Subway policy. The system never decides a purchase, grants an approval or infers official tolerance thresholds. Missing currency, full-order comparison scope, due dates, parent records and reservations remain missing.

Budget comparison requires the PO's declared budget to agree with its line-item budget, an existing native finance location, matching source period labels and established currency compatibility. It compares the exact PO-line allocation to availableAmount at snapshot time, not a reconstructed earlier balance. Source currency is absent, so real-source budget comparisons correctly remain qualified. Supplier totals group recorded PO value by raw vendor code and currency and explicitly cover only the selected page; they do not assert central-supplier identity or population rankings.

## E. Reconciliation and bounds

Receipts reference PO line `_id` through `receivedItems[].poItemId`. Quantities are aggregated per PO line across distinct receipts, retaining partial/matched/over-received/insufficient outcomes. Missing or duplicate PO line IDs, repeated receipt-line references, invalid quantities and unmatched references remain explicit. Draft/rejected/reconsidered/cancelled receipt quantities are excluded from booked quantities with a qualification, following the source's submission/reversal distinction. Booked quantities are not independent proof of physical delivery.

Header amounts are never multiplied through receipt or item fanout. Exact decimal calculations use a 38-digit arithmetic context. Invoice amount comparisons require established currency and full-order scope; invoice item reconciliation and overdue status remain unavailable in real records. An exact difference is an analytical review observation, not overbilling or fraud.

Production assessments operate on at most 20 selected base records per page, plus at most 5,000 related records and 8 MB of source projections, with a deadline and an 800 KB result bound. Exceeding a bound fails rather than returning an unqualified partial assessment. Complete base-query counts and pagination are preserved. A page never establishes an exhaustive population assessment; ordinary population aggregates continue through the existing Subway query tool.

Record hashes cover normalized allowlisted projections, not entire original BSON documents. Assessment receipts bind the request, output, source authority, tenant and knowledge hash. Source generation/credential changes are rechecked after retrieval. Historical source attestations remain historical regardless of read time.

## F. Existing pipeline integration

Metadata discovery receives source-scoped status meanings. Relevant identity/state/date/rule/readiness definitions enter the existing planning context within bounded allowances. The existing registered document reader retrieves exact new code passages with offsets and hashes. OpenAI planning can select the registered assessment tool; CrewAI and GraphRunner execute it under normal grants and receipt validation. Adaptive evaluation receives supported findings, missing prerequisites and source freshness limitations, and retains its existing conditional retrieval/replanning behavior.

The existing Knowledge Map highlights actual source-field usage and displays applied rule IDs, outcomes and extension version in its existing evidence descriptions. Detailed outcomes remain in the tool/report evidence; no new frontend node type or separate graph UI is added. The underlying saved v4 graph remains unchanged.

Existing schedules, Gmail and Calendar behavior remain unchanged. New recurring assessments require exact reviewed inputs and current knowledge; relative periods cannot silently drift or bypass reviewed date bounds. Existing ordinary recurring queries retain their original consent schemas.

## G. Verification evidence

See `openspec/changes/subway-procurement-knowledge/verification.md` for final commands, counts and the acceptance matrix. Real-source rehearsals use copied application stores and the existing read-only restricted MongoDB reader. No source write, live workflow submission, paid model request, email, Sheet write or Calendar action is performed by verification.

The first broad run exhausted the host filesystem during temporary-store setup and is not counted as a passing run. Only task-owned rehearsal copies and temporary test stores were removed; source records and other backups were preserved. Final runs use isolated memory-backed temporary storage.

## H. Remaining limitations

Implemented and verified: typed domain checks, source-scoped identity/status/date definitions, bounded native traversal, PO/receipt line reconciliation, prerequisite reporting, document citations, platform runtime/evidence/map integration and isolated modeled scenarios.

Missing authoritative policies: company approval matrices, tolerance thresholds, corporate fiscal boundaries and official identity ownership. None is labeled verified company policy.

Unavailable real business evidence: no populated PO purchaseRequestId, no pr_approval records, no populated reservation amounts, no invoice currency/items/dueDate, no budget-line currency, incomplete cross-system store/vendor identity, and no current synchronization. Scenario success does not fill those source gaps.

Unverified live integrations: paid OpenAI selection quality for arbitrary live prompts and actual external mail/Calendar/Sheets delivery are not certified by controlled-model and dry-run tests. Complete arbitrary-population item reconciliation requires explicit paging and evidence scope; a bounded assessment page is not a population-wide accounting audit.
