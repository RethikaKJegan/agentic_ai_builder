# Chunk 1 verification

## Scope
Source discovery and mapping only. No new UI, business ontology runtime, extraction service, publication or deployment is claimed.

## Checks
- `.venv-integrations/bin/python -m pytest tests/test_simpson_business_sources.py tests/test_simpsons_field_verification.py -q`: 13 passed; two existing jsonschema RefResolver deprecation warnings.
- `/home/raf/.nvm/versions/node/v22.23.3/bin/openspec validate simpson-business-ontology --type change --strict --json`: valid, zero issues.
- `scripts/verify_simpson_business_sources.py`: both current scoped Simpson sources read successfully; 21 selected collections, 19 sampled and two empty; six direct-reference checks completed. See `docs/simpson-business-ontology/source-verification-2026-10-31-v2.json` for timestamp, exact bounds and outcomes.
- Initial evidence preserved; corrected product/stock field selection recorded in v2 and mapping inventory.
- Two unresolved replacement-to-ticket references among 100 sampled requests are non-blocking. Owner explicitly accepted proceeding with resolved records; retain unresolved records separately without invented associations.
- Aggregate-only output: no source records/identifiers/values/credentials exported. Zero company writes, ontology mutations and model calls. Connector configurations compared unchanged across verification.

## Limits
First 100 unsorted records, not population completeness; type presence is not value validity. Cross-database associations, physical-engine identity, policy exclusions and exact deployed backend correspondence are not verified. No runtime or frontend tests were necessary because neither implementation was changed. Existing uncommitted work was preserved.

## Next chunk
Implement isolated persistence/API and Business Ontology tab under a separate verification step. All later tasks remain unchecked.

# Chunk 2 verification

## Delivered
- Separate `business_ontology_*` persistence, tenant/owner namespace, immutable foundation snapshot and initialization audit event.
- Separate GET state, POST initialize and GET version APIs with session/origin transport, scope checks and exact initialization payload validation.
- New Business Ontology tab using `SimpsonBusinessOntology.tsx`: both source roles, explicit initialization, revision/current-source status, five layer filters, twelve modules and honest zero concept/rule counts.
- No model calls, source queries, company writes, generation, graph construction, SME validation or publication in this chunk. Operational business approvals remain in module scope.

## Passing checks
- `.venv-integrations/bin/python -m pytest tests/test_business_ontology.py tests/test_ontology_foundation.py tests/test_ontology_objects.py tests/test_data_sources.py -q`: **99 passed**. Covers persistence across restart, identical initialization, ownership/workspace/scope isolation, immutable versions, disconnected/changed metadata, malformed payloads, actual HTTP session/origin checks, unchanged legacy ontology and unchanged connection rows.
- Frontend targeted Vitest: **34 passed** across SimpsonBusinessOntology, original BusinessOntology, DataIntelligence, OntologyFoundation, OntologyGraph and OntologyObjects.
- `npm run typecheck`: passed. `npm run lint`: passed without warnings after the request-cleanup adjustment.
- `npm run build`: passed on retry. The first build compiled/typechecked but stopped on the installed Next.js security advisory notice; retry completed successfully while retaining the advisory. No dependency upgrade was performed.
- `BUILDER_LOGIN_SECRET=<isolated fixture key> npm run test:e2e -- e2e/simpson-business-ontology.spec.ts`: **2 passed**, desktop and 390px mobile. Exercises layer/module navigation, both source choices, one initialization request, reload, and switching to the original Ontology tab without legacy mutations; zero page errors and no horizontal overflow. New API calls are intercepted browser fixtures; actual persistence/auth/HTTP behavior is verified separately in backend tests, not against production.
- Screenshots visually inspected: `frontend/test-results/simpson-business-ontology-desktop.png` and `simpson-business-ontology-mobile.png`.
- Shared contract schemas/fixtures valid; strict scoped OpenSpec validation valid with zero issues; `git diff --check` passed.

## Preservation and limits
A component-name collision discovered by validation was corrected by moving the new component/tests to SimpsonBusinessOntology names and restoring the original tracked BusinessOntology component/tests byte-for-byte. `git diff --exit-code` confirmed no changes to those original files. Existing uncommitted source/UI/ontology work was retained.

Implementation and isolated verification only: no deployment, service restart, live foundation initialization, production data migration or source configuration change was performed. SQLite persistence is verified; this chunk does not claim a live PostgreSQL deployment. Next.js tooling reported a security advisory for the installed dependency; dependency remediation is separate from this feature.

Ready for chunk 3: existing-OpenAI extraction and versioned structured business definitions. Compiler, populated business graph, executable rules and intelligence remain unfinished later tasks.

## Subsequent security remediation

The owner subsequently requested the Next.js fix. Next.js was updated to 16.4.3 and verified locally; its advisory and build warning are resolved. See `openspec/changes/next-security-patch/verification.md` for current test results, remaining unrelated audit findings and the unchanged live-deployment status. Earlier chunk-2 advisory observations above are historical.

# Chunk 3 verification — 2026-10-31

## Delivered

- Scoped immutable evidence documents, sanitized blueprint/backend reference import and metadata-only context from both bound sources.
- Durable single-module generation jobs with current ownership/authorization, idempotency, cancellation, source/revision checks and atomic draft snapshots. Existing local and supervised workers use the configured OpenAI provider; no Bedrock dependency or model substitution.
- Strict structured output plus local evidence, ID/reference, cycle and cross-module dependency validation. Candidate rules remain non-executable, with source basis, unknowns and unresolved questions retained.
- Explicit source/generation controls, polling, evidence inspection, actual counts, draft definitions and historical version browsing in the separate Business Ontology tab. Existing Ontology and Semantic Intelligence remain available.

## Passing checks

- Backend business/foundation/object/source regression run: **118 passed**. After adding HTTP source/job and idempotent sanitized-import coverage, the final `tests/test_business_generation.py` run passed **21 tests** (overlaps the broader run; counts are not additive).
- Live-provider/worker/manual-worker-authorization regression suites: **43 passed**. These are isolated fixture tests and do not send additional model requests.
- Frontend data-source/API-proxy/workspace-authorization regressions: **110 passed in 18 files**.
- TypeScript, ESLint and production build passed on Next.js 16.4.3. The earlier security patch's remaining unrelated audit findings are not claimed resolved by this chunk.
- Playwright: **6 passed**, covering new extraction, separate Simpson foundation and existing Ontology lifecycle on desktop and mobile. Evidence quotes, candidate-rule status, unknowns, immutable version selection, source controls and legacy navigation exercised. Requests are intercepted browser fixtures; backend persistence/auth behavior is tested separately.
- Visually inspected `frontend/test-results/business-extraction-desktop.png` and `business-extraction-mobile.png`; readable layouts and no horizontal overflow. An initial browser assertion matched both a revision label and a version option; making the assertion exact resolved the test ambiguity, and all six flows passed.
- Shared workflow/agent/tool contract schemas and fixtures valid; strict scoped OpenSpec validation valid with zero issues.

## Approved real-provider smoke

Automatic approval review initially rejected sending the prepared database-derived field metadata and private reference excerpts to OpenAI without specific consent. No request was sent by that rejected command. After reviewing the explanation, the owner explicitly selected **“Approve this one smoke test.”** Exactly one request was then sent using the exact prepared payload; no automatic retry or second real call was made.

Configured model `gpt-5.6-luna` succeeded: **14 concepts, 7 relationships, 2 candidate rules**, 7,306 input / 3,717 output tokens. Strict structure, evidence quotes and references passed. The two rules retain proposed-logic versus descriptive-implementation bases and are non-executable. Missing policy/exclusion evidence remains unresolved.

Private exact payload and isolated store: `.local/business-ontology/chunk3-payload-review/`. Result report: `report-real.json`. No credentials or company records were sent; the input contained reference excerpts and saved field names/types. Zero company queries/writes, copied connector secrets or live application mutations. This evidence verifies extraction, not warranty-policy correctness or completeness.

## Limits and handoff

Implemented and verified locally only: no deployment, service restart, live Business Ontology initialization or live draft publication. No changes to shared execution contracts or existing ontology records. Source documents are evidence rather than execution instructions; automatic validation checks are not business approval. No SME ontology validation gate is included.

Chunk 3 is complete. Next chunk is OWL/RDF and SHACL compilation with automated validation; executable rules, competency queries, populated graph mappings and intelligence remain unchecked later tasks.

# Chunk 4 verification — 2026-10-31

## Delivered

- Deterministic immutable-version compiler for OWL classes/inheritance, concept-scoped attributes, relationship object properties, source evidence and annotated non-executable rule candidates. RDF/OWL Turtle and RDF/XML exports preserve the same graph.
- Instance SHACL shapes plus separate definition-validation shapes. Draft structure/citations/hierarchy are rechecked, both shapes graphs are meta-SHACL validated, and the actual generated ontology definitions are SHACL checked. No remote imports, inference, custom SPARQL, JavaScript or rule execution.
- Scoped additive compilation persistence and GET/POST version APIs, canonical input and file hashes, idempotent audit event, immutable-input recheck and manager/write authorization. Historical exports remain independent of current connections and the current draft revision.
- Selected-version report/export panel with explicit compilation, viewer browsing/downloads, safe read recovery, stale-response protection, unresolved information and six export artifacts. No SME validation gate or deployment.
- Offline diagnostic script opens only an explicitly scoped application store in SQLite read-only mode and writes a fresh private export directory. No environment credential loading or application-service startup.

## Passing checks

- `tests/test_business_compiler.py`: **20 passed**. Covers meaningful SHACL failures for missing required attributes, invalid datatype values and wrong relationship targets; RDF/XML/Turtle graph equivalence; rule non-execution; deterministic escaping/serialization; evidence/hash/reference/hierarchy corruption; scope/write permissions; historical/read-only/idempotent access; mid-compilation snapshot drift; foundation rejection; actual HTTP endpoints and no-store envelopes.
- Existing business/foundation/object/source regression suites: **120 passed**. Existing deprecation warnings only. Compiler tests are additional to this run.
- Frontend data-source, API-proxy and workspace-auth regressions: **115 passed in 19 files**. Compilation tests cover explicit submission, actual artifact download, viewer restrictions, safe failure/retry reads and late results while switching versions.
- Required frontend domain regression suites: **72 passed in 10 files**.
- TypeScript, ESLint and production build passed on Next.js 16.4.3. RDFLib 7.6.0 / pySHACL 0.40.2 installed in the local integration environment; `pip check` found no broken requirements. Root requirements updated for a later backend deployment.
- Playwright: **8 passed**, desktop/mobile compilation+download, business generation, separate Simpson foundation and original Ontology lifecycle. Download bytes/filename checked, historical version hides the newer artifact, returning restores the persisted result without another mutation, zero page errors and no horizontal overflow. Browser routes use fixture responses; actual API/auth/persistence semantics are covered by backend tests.
- Screenshots visually inspected: `frontend/test-results/business-compilation-desktop.png` and `business-compilation-mobile.png`. Validation status, warnings, download controls and provenance are readable on both layouts. After improving the technical-check labels and aligning fixture module counts, types/lint, the five compilation UI tests, build and both compilation browser flows were rechecked.
- Shared execution contract schemas and fixtures valid. Strict scoped OpenSpec validation valid with zero issues. `git diff --check` passed. Original tracked Semantic Intelligence component/tests show no diff.

## Offline check using the prior real-model draft

The earlier approved chunk-3 warranty draft compiled successfully without a new model call: **14 concepts, seven relationships, two non-executable rules, 525 ontology triples and 182 instance-shape triples**. All four technical checks passed, with **31 retained warnings** for unknowns, questions and mapping limits. No company-instance validation or OWL reasoning was run; business policy remains unverified.

Private evidence: `.local/business-ontology/chunk4-offline-check/manifest.json`, `validation-report.json`, and the six generated exports. Source input: the existing chunk-3 isolated store, opened read-only. Zero model calls, company queries/writes and input-store writes. These results were not published into the live Business Ontology workspace.

## Boundaries and next chunk

Compilation conformance describes the structured definitions and generated shapes, not policy completeness or correctness, engine-instance data quality, rule execution or a populated company graph. The instance-shape meta-check uses an empty graph only to validate the shape definitions; no empty-data conformance is presented as instance validation. Reference targets and enumeration values absent from the draft are reported rather than invented. Attribute evidence inherits the concept's citations because the draft schema has no attribute-level citations.

No deployment, service restart, live initialization/migration, company-data write, additional OpenAI transfer or shared execution-contract change. Existing uncommitted work retained. Next chunk: source-backed rule catalogue and competency queries; graph mappings and intelligence remain subsequent tasks.

# Chunk 5 verification — 2026-10-31

## Delivered

- Read-only immutable-version rule catalogue preserving evidence basis, quoted source provenance/hashes, conditions/outcomes, direct input concepts/attributes, unknowns and module questions. Input data availability remains not_checked and all rules non-executable/unverified.
- Six code-owned bounded SELECT queries over the selected owned passed compilation: rule inputs/evidence, policy/implementation candidates, concept relationships and unresolved information. Existing read permissions apply even though execution uses POST. Caller SPARQL, external IRI focus, foreign/missing definitions and invalid pagination are rejected.
- Compilation/version/compiler/report/input/artifact integrity checks before local RDF parsing. Missing or failed prerequisites are separate from an actual empty query result; no auto-compilation or query execution on selection changes. Ordered pages and query/compiler/input/graph provenance retained.
- The 22 supplied blueprint business competency questions with source hash/section and explicit instance/policy/temporal/identity/confirmation/exposure prerequisites. None is claimed answerable from concept names or schema alone. The excluded SME review instructions were not implemented.
- Selected-version UI with module/basis/text rule filters, inputs/evidence/unknowns, explicit definition query/focus/page controls, readiness refresh after compilation, stale-result discard and business-data prerequisites. Existing Ontology and Semantic Intelligence remain separate.

## Passing checks

- Business rules, compiler, generation, foundation, ontology-object and source backend regressions: **168 passed**. Includes 28 rule/query cases with actual RDF results, genuine empty results, policy/implementation separation, stable pages/focus, malformed/injected requests, damaged artifacts, missing/failed compilation, historical/foreign access and an actual viewer HTTP query with unchanged version/job/compilation/event counts. Existing deprecation warnings only.
- Frontend source/API-proxy/workspace-auth/domain regression suites: **195 passed in 30 files** after the rendering fix. Includes rule evidence/input display, unavailable-question prerequisites, explicit query-only behavior, focus/question/version stale-result handling, safe failures, readiness refresh and an integration test ensuring one compiler and one catalogue after refresh.
- TypeScript, ESLint and Next.js 16.4.3 production build passed after the final UI fix.
- Playwright: **10 passed** after both fixes, covering rules/query pages, compilation/downloads, generation, separate Simpson foundation and original Ontology lifecycle on desktop and 390px mobile. Explicit compilation refreshes readiness without querying; evidence, attributes, result bytes/pages, question clearing and historical-version prerequisites are checked. Zero page errors and no page-level horizontal overflow. Browser requests are intercepted fixtures; actual RDF/API/auth/no-write behavior is covered separately by backend tests.
- Visually inspected `frontend/test-results/business-rules-desktop.png`, `business-rules-mobile.png` and `business-rule-query-desktop.png`. Controls, evidence and result pages are readable; wide query tables scroll within their container on mobile.
- Shared workflow/agent/tool contracts valid; strict scoped OpenSpec validation valid with zero issues; `git diff --check` passed. Original tracked Semantic Intelligence component/tests have no diff.

## Offline real-draft query evidence

`scripts/check_business_rules.py` read the existing chunk-3 isolated store using SQLite mode=ro and existing chunk-4 artifacts. The prior real-model draft has **two candidates: one descriptive implementation, one proposed logic, zero policy statements**. All six fixed queries completed: 11 input rows, two evidence rows, zero policy candidate rows, four implementation-condition rows, seven relationship rows, 29 unresolved-information rows. All pages complete at limit 50.

Private report: `.local/business-ontology/chunk5-offline-check/report.json`; exact results: `query-results.json`; catalogue: `rules.json`. Zero model calls, company queries/writes, input-store writes and rule execution. No credentials loaded or live application services started. Zero policy candidates describes only this saved draft; it does not establish absence of policy documents in company systems.

## Browser regressions found and corrected

The first desktop/mobile run exposed duplicate compilation controls after refreshing query readiness. The compiler and rule panels had the same sibling React key. Each panel now has a distinct version-qualified key, and the integration regression verifies one compiler and one catalogue after explicit compilation. This was corrected in product code, not hidden with a first-match browser selector. A subsequent browser flow exposed the catalogue retaining its initial module filter when navigating to Warranty; it now follows the selected business module without running a query, with a dedicated regression. Types/lint, all 195 frontend/domain tests and production build were rechecked after the fixes.

## Limits and next chunk

Only definition-level queries are implemented. Company-instance query templates and answers require later mapped graph and sufficient policy/evidence. Declared required fields are not validated company values; candidate policy statements are not business approval. No SME gate, graph ingestion, eligibility decision, rate calculation, publication, deployment, service restart or shared execution-contract change. Existing uncommitted work retained.

Next chunk: knowledge graph mappings and the engine-to-monitoring path using both sources, preserving unresolved associations and policy/data gaps.

# Chunk 6 verification — 2026-10-31

## Delivered

- Code-owned 21-collection mapping catalogue from the reviewed blueprint/backend/source-discovery field allowlist and current metadata. Explicit generated concept/attribute bindings; no label inference. Scalar nested projection preserves missing/null/unsupported/over-limit states and excludes credential/binary/document/object fields.
- Explicit exact-serial graph build over both owned sources; 20 retained records plus one truncation probe per queried collection, 25-second overall deadline, bounded Mongo operations, reused per-source connections and 2 MB result cap. Collection unavailability/no usable values/no matches/out-of-path/truncation are distinct. Company execution failure discards the graph.
- Source/collection/native BSON-typed identity; strict same-source reference matching; candidate-only serial and engineering-scope edges; unresolved references retained. No physical-engine merge, invented ticket association, incorporation claim or recurrence inference.
- Local mapped RDF and saved-shape validation with actual violations, failed conversions, mapped-record counts and honest not_run for zero mapped records. Mapping meaning/business policy remain unverified. Monitoring prerequisites and warranty evaluation not_run remain visible.
- Scoped immutable graph snapshots and audit, current authority/source/credential/metadata/definition drift checks, stable completed-request idempotency and concurrency admission. A final regression verifies that overlapping independent builders commit one graph and one audit event for the same request.
- Selected-version mapping controls, explicit build/save, historical snapshot reads, interactive graph, record/edge/outcome inspection, stage counts, validation reports and RDF exports. Viewers cannot build. Opening the UI or inspecting saved snapshots does not query company sources.

## Passing checks

- Graph/business/rules/compiler/foundation/object/source backend suite: **187 passed**. After adding database-level overlapping-builder deduplication, the final graph suite passed **20 tests** (overlaps the broader run; do not add these counts). Includes typed ID separation, exact references, no cross-source identity merge, source failure without partial save, drift/revocation, field restrictions, idempotency, bounded truncation, conversion/SHACL failures, read-only/viewer access and actual HTTP route/scope/payload tests. Existing deprecation warnings only.
- Frontend data-source/API-proxy/workspace-auth/domain regressions: **198 passed in 31 files**. New tests verify no automatic source build, required explicit bindings, viewer-only saved reads and stale graph discard on version changes. The remaining generation/compilation/rule tests retain prior behavior.
- TypeScript, ESLint and Next.js 16.4.3 production build passed. After inspecting the first phone screenshot, source groups were stacked with larger labels; types/lint/build and both graph browser cases were rechecked.
- Playwright: **12 passed**, desktop/mobile graph mapping/build, interactive record selection, candidate-edge inspection, RDF download, historical graph removal, and existing rule/query/compilation/generation/Simpson-foundation/original-Ontology flows. New graph requests are intercepted fixtures; actual connector/API/auth/persistence semantics are independently covered. Zero page errors and no page-level horizontal overflow.
- Visually inspected final `frontend/test-results/business-graph-desktop.png` and `business-graph-mobile.png`: readable phone nodes, dashed candidate link, zoom/pan controls and record inspector. Browser fixtures are not company evidence.
- Shared execution contracts valid; strict scoped OpenSpec valid with zero issues; `git diff --check` passed. Original tracked Semantic Intelligence component/tests have no diff.

## Real bounded source checks

`scripts/check_business_graph.py` opens live application connection/metadata rows with SQLite mode=ro, decrypts credentials in memory and uses a fresh private application store with safe copied metadata and the earlier actual OpenAI draft. The explicit diagnostic binding maps the known `warranty:engine_instance.serial_number` to `enginedetails.engineSerialNumber`. It does not initialize or migrate the live business workspace.

1. Invoice-anchored report: **one service invoice**, no ticket/manual-claim/SAP-claim/QA match; one mapped record passed structural instance validation.
2. Ticket-anchored report: **four service records** (two tickets and their OEM/account organization records), **four direct references and one candidate serial edge**. No invoice matched, so zero mapped records and instance validation correctly not_run. No matching claims or QA records were invented.
3. QA-anchored final report: **one service invoice and one quality failed-engine analysis**, **one candidate serial edge**, one mapped invoice record passed structural instance validation. Both databases returned real records. Of eight bounded QA serial candidates, four did not satisfy the current diagnostic anchor-format contract and were not normalized. This is not a claim that those business identifiers are invalid.

Final private evidence: `.local/business-ontology/chunk6-connector-check/report.json`, `chunk6-ticket-check/report.json`, and `chunk6-quality-valid-anchor/report.json`; records/RDF live only in each private isolated store. Initial QA diagnostic attempts were unavailable: the anchor's source-role selection was corrected, then bounded usable-anchor selection was added after an exact-input validation failure. Failed attempts are not counted as successful QA verification.

Successful checks record zero company writes, OpenAI/model calls, live application writes and copied connector secrets. Connector configuration fingerprints remained unchanged. Both sources were queried in each successful graph path, but none of these serials returned manual/SAP claim records. CAPA lacked supported current scalar identity metadata and stayed unavailable; other non-serial-path collections were not scanned. No monitoring effectiveness/rates were asserted.

## Limits and next chunk

This is a bounded record-level source graph with explicit user mappings and independent source read times, not a complete history, physical-engine master, shared database snapshot or approved semantic integration. The two previously accepted dangling replacement references are not repaired or assigned to an engine by guesswork. A targeted serial path cannot enumerate every orphan record. The current exact-input identifier format and scalar-field limits remain explicit.

A passing mapped-instance check establishes only the chosen projection's saved-shape conformance. Business mapping meaning, warranty policy, applicable exclusions, engineering-change incorporation, confirmed comparable failures and exposure denominators remain unverified/missing. The 22 instance business competency questions are not automatically promoted to answerable because a source graph now exists.

No deployment, service restart, live Business Ontology initialization, company writes, source configuration change, new model transfer, SME gate, policy execution or shared execution-contract change. Existing uncommitted work retained. Chunk 6 is complete within its bounded mapping/path scope. Next chunk: remaining modules and evidence-backed intelligence, with broader graph coverage and actual instance competency answers gated on sufficient policy/data.

# Chunk 7 verification — 2026-10-31

## Delivered

- Curated supplied-blueprint reference kit: all twelve modules, 67 concepts, 14 relationships and three non-executable proposed rules, with exact quotations and verified source-bundle hash. Business diagram groupings do not become inheritance. Optional attributes and explicit unknowns preserve policy/identity/monitoring gaps.
- Explicit manager-only add-missing-module import with immutable cumulative version, preserved existing module definitions/history, original connected-source binding, current authority/revision/source checks, active-generation exclusion, atomic audit and stable retry idempotency. No model/token output is fabricated. Missing cross-module IDs produce binding questions rather than inferred matches.
- Selected-version module/evidence/gap coverage, curated reference origin in version/item inspection and explicit import in the separate Simpson Business Ontology tab.
- Six fixed reports on immutable saved graphs: service path, separate claim fields, inspection findings, quality/change evidence, recorded calendar dates and evidence gaps. Scoped graph/version reads verify projected-record hashes and edges. Rows cite record/field/hash, distinguish candidate/direct associations and retain missing/unprojected/invalid/truncated states. Actual source codes and possible causes are not interpreted as approved decisions or confirmed root causes.
- Explicit report execution, bounded pages, source-record inspection, JSON report-page export, input/result hashes and visible unavailable conclusions. Reports make no database-source/model calls, execute no rules, and remain available for owned historical graphs when connectors disconnect.

## Passing checks

- Broad backend suite: **216 passed** across Business Ontology/generation/compiler/rules/graph/reference/intelligence/actual HTTP transport and original foundation/object/source regressions. Existing jsonschema/FastAPI deprecations only. Includes preserving existing modules, complete kit compilation, immutable history, source binding/permission/revision/active-job rejection, stable import retries, report corruption checks, bounded request validation and historical scope isolation. Actual HTTP checks verify session/origin/no-store behavior and no network during report execution.
- Affected frontend/API-proxy/auth/domain suite: **203 passed in 32 files**. New tests cover explicit import with stable retry key, manager/viewer/historical access, explicit fixed report execution, pagination, source inspection, empty evidence wording and stale response discard. After the final origin wording change, 15 targeted UI tests passed again (overlapping).
- TypeScript, ESLint and Next.js 16.4.3 production build passed on final product code.
- Playwright: **14 passed**, desktop/mobile reference import/preserved historical definitions, saved report execution/paging/source inspection/export, and prior graph/rules/compiler/generation/Simpson foundation/original Ontology flows. Intercepted browser fixtures make no company/model calls or legacy writes; actual transport/persistence/source semantics are independently covered by backend tests. Zero page errors and no page-level horizontal overflow. An initial new test used a capitalized module selector inconsistent with the real “Investigation and inspection” label; corrected to its scoped accessible button. Final focused phone screenshots were visually inspected: module cards, curated-origin/evidence detail, observation cards, pagination, exports and provenance remain readable without horizontal overflow. These are intercepted fixtures, not company evidence. Focused screenshots are recorded in `frontend/test-results/business-coverage-*.png`, `business-reference-detail-*.png`, and `business-intelligence-*.png`.
- Shared execution contracts valid; scoped strict OpenSpec valid with zero issues; `git diff --check` passed. Original Semantic Intelligence component/tests have no tracked diff.

## Offline real-evidence checks

The three earlier private source graph stores were opened with SQLite mode=ro; source credentials were not loaded. All six questions ran on each original saved graph/version. The expanded reference draft was checked separately in memory, preserving all 14 actual generated warranty concepts and adding eleven missing modules, for **73 concepts**. All three expanded drafts passed compilation. Saved input-store file hashes remained unchanged.

| Previously saved path | Records | Report evidence |
| --- | --- | --- |
| Invoice | One service invoice | Two dated-field rows; 29 gaps; no service/claim/inspection/quality observations |
| Ticket | Four service records | Four service-path rows; four dated-field rows; 35 gaps; no claim/inspection/quality observations |
| QA | One service invoice plus one quality analysis | Seven quality-field rows; three dated-field rows; 28 gaps; no claim/inspection observations |

Field rows include explicit missing/unprojected values; counts do not imply complete recorded values. No absent claims, confirmed causes or recurrence outcomes were invented. Private initial offline evidence is `.local/business-ontology/chunk7-offline-check/report.json`. The reproducible `scripts/check_business_intelligence.py` was also run on the saved two-source QA graph; evidence is `.local/business-ontology/chunk7-offline-reproducible/report.json`. Both report zero company queries/writes, model calls and input/live-store writes.

## Completion boundary

Chunk 7 is complete locally for reference drafts and saved-evidence intelligence; it is not deployed. Draft coverage does not mean all live business instances are populated/validated. Complete versioned warranty policy/exclusions, physical-engine identity, confirmed comparable failures, change incorporation, operating exposure and population denominators remain data-dependent follow-up. Eligibility/root cause are not evaluated; recurrence/rates/effectiveness remain unavailable. Full business competency answers and production acceptance remain open tasks. No SME gate, extra OpenAI transfer, company write, source configuration change, live Business Ontology initialization, service restart, deployment or shared execution-contract change. Existing unrelated uncommitted work retained.

# Chunk 8 verification — 2026-11-01

## Delivered

- Explicit input preparation for one saved service complaint in an owned immutable graph/version. Retains literal projected field states, source record/collection/field/hash and separately normalized values. Complaint sale date/hours, serial, OEM, alternate ticket hours and creation date stay distinct; no claim/inspection/alternate fallback substitution.
- Strict nonnegative finite plain-decimal parsing, including zero, and ISO date/datetime parsing with precision/timezone qualifications. Invalid dates, nonnumeric/unit/grouped/exponent/non-ASCII/boolean/negative/nonfinite/overlong hours remain unusable; no missing value or assessment date is inferred.
- Separate saved invoice candidates with exact public-value serial/OEM comparisons, per-field evidence and no selection/merge. Missing/mismatched/multiple invoices, invalid invoice dates, conflicting hour observations, truncation and mapped-shape status remain visible. Saved public comparisons do not reconstruct native BSON field types or establish identity.
- Explicit Requires Review readiness with eligibility not_evaluated, applicable policy/identity/assessment-time requirements, immutable-version policy-kind document references with unestablished authority, saved source outcomes and graph/definition/result hashes. Policy documents, stored warranty flags and supplied code thresholds do not configure executable authority. No SME workflow, warranty denial or business decision persistence.
- Read-only scoped POST `/versions/{version_id}/graphs/{graph_id}/warranty-readiness` accepting exactly `{ticket_node_id}`, existing session/origin/no-store behavior, saved graph/version/record integrity checks, no extra table and no source/model calls. Historical owned reads remain available after connector disconnects.
- Saved graph UI with explicit complaint selection/preparation, independent case results, review reasons, source inspection, candidates/policy/coverage details and JSON report export. Empty-ticket graphs have no prepare action; stale results are discarded on case/graph/version changes.

## Passing checks

- Broad backend suite: **260 passed**, including 44 new warranty readiness checks and all earlier Business Ontology/generation/compiler/rules/graph/reference/intelligence/HTTP/foundation/object/source regressions. Existing jsonschema/FastAPI deprecation warnings only. New coverage includes numeric zero/invalid formats, leap dates and offset validation, complete-looking inputs without policy authority, separate ticket inputs, no substitution, ambiguous/mismatched invoices, field conflicts, truncation, corruption, historical disconnection and owner/workspace isolation.
- Actual HTTP tests verify missing session, untrusted origin, exact payload, non-ticket rejection, no-store success, foreign scope rejection and unchanged workspace/version/graph/event/connection rows. Socket network access is denied during saved-case preparation checks.
- Affected frontend/API-proxy/auth/domain suite: **208 passed in 33 files**, including explicit action/selection, missing primary versus alternate hours, source inspection, no-ticket state, safe retry and discarded late results across ticket and version changes.
- TypeScript, ESLint and Next.js 16.4.3 production build passed.
- Playwright: **14 passed**, desktop/mobile warranty preparation/source inspection/JSON export plus prior graph/intelligence/reference/rules/compiler/generation/Simpson foundation/original Ontology flows. Exported JSON was read and checked for exact selected ticket, Requires Review, eligibility not_evaluated and zero source/model calls. Case deselection clears readiness. No page errors, page-level horizontal overflow or legacy ontology writes. After improving screenshot capture, the two graph/warranty browser cases passed again (overlapping). Final desktop/mobile viewport screenshots `frontend/test-results/business-warranty-*.png` were visually inspected: status, review reasons, separate hour cards and source links remain readable. Browser fixtures are not company evidence.
- Shared execution contracts valid; strict scoped OpenSpec valid with zero issues; `git diff --check` passed. The initial overlong OpenSpec requirement was shortened while preserving its scenarios. Original tracked Semantic Intelligence component/tests have no diff.

## Offline real evidence

`scripts/check_business_warranty.py` read all three previous private graph stores with SQLite mode=ro and no credential access. It verifies input file hashes and writes only a fresh private evidence directory. No company/model services or live application writes were used.

- Ticket graph: four service records, **two separate complaints**. Both have parseable complaint sale dates and complaint hours, serial and OEM observations. Alternate top-level hours were not projected. No saved invoice candidates or policy-kind documents exist in that graph/version. Both reports correctly remain Requires Review for missing applicable configured policy, unresolved identity, unspecified assessment-time basis, no saved invoice and instance validation not_run. No date default, eligibility inference or source change occurred.
- Invoice-only graph and two-source QA graph: zero saved tickets; no readiness cases invented.
- All input-store file hashes stayed unchanged. Each summary reports company_queries=0, company_writes=0, model_calls=0, input_store_writes=0, rules_executed=false and business_policy_verified=false.
- Private evidence: `.local/business-ontology/chunk8-chunk6-ticket-check/report.json`, `chunk8-chunk6-connector-check/report.json`, `chunk8-chunk6-quality-valid-anchor/report.json`; full individual ticket reports remain private in the ticket evidence directory.

## Completion boundary

Chunk 8 is complete locally as warranty input preparation, not deployed. It does not claim the complete authoritative policy, confirmed physical-engine identity or executable eligibility rule. Those data-dependent tasks and monitoring/full competency/production acceptance remain explicitly open. Next implementation can add structured versioned policy intake and applicability once authoritative source information is available, preserving current code behavior as implementation evidence. No additional model transfer, company write, source configuration change, live ontology initialization, service restart, deployment, shared execution-contract change or unrelated-work reset occurred.

# Chunk 9 verification — 2026-11-01

## Delivered

- Scoped immutable policy draft revisions in additive `business_policy_heads`/`business_policy_versions`, separate from ontology definition versions. Sources must be owned policy-kind Warranty documents with valid text hashes. Each known clause needs an exact nonblank quotation; unknown value/quote pairs stay null. No real policy is seeded from code, flags or blueprint examples.
- Guided policy document intake and optional clause fields for source version, effectivity, OEM/model reference values, date basis/bounds, coverage limits/notes and exclusions. Full policy/source provenance and quoted clauses remain inspectable/downloadable. Draft values are manager-supplied interpretations; exact citation checks do not verify authority or semantic correctness. No SME workflow, publication or executable policy state.
- Expected per-series revision, current write authority, stable request-key fingerprint, atomic head CAS/version/audit persistence and bounded storage. Identical retries/concurrent requests return one revision, stale bases/changed-key payload reuse fail without partial writes; old policies/ontology/graphs remain immutable. Source text and metadata are retained in exports so saved hash inputs are preserved.
- Explicit saved-case scope/date comparisons selecting one exact saved policy revision, ticket, timezone-qualified assessment timestamp and optional saved service invoice. Declared OEM/model values compare without aliases/coercion/native BSON reconstruction; effective dates use declared assessment/sale/selected-invoice basis and inclusive/exclusive bounds. Missing end/basis/invoice/data remains unavailable rather than unbounded or guessed.
- Comparisons show candidate match/different/unavailable, exact policy clauses/quotes, source field evidence and policy/source/graph/definition/result hashes. Every result stays Requires Review, eligibility not_evaluated, policy authority unverified, identity unresolved, limits/exclusions non-executed. A differing observation is not claim denial. No source/model call or company/decision write.
- Scoped no-store GET/POST policy library, immutable policy GET and fixed saved-case comparison POST through existing session/origin transport. Viewers inspect/run comparisons; only current managers save drafts. UI selects explicit inputs, clears stale results and supports policy/report downloads. Existing chunk-8 input preparation and original ontology tabs remain independent.

## Verification evidence

- Broad backend suite: **292 passed**, covering new policy tests plus prior ontology/generation/compiler/rules/graph/reference/intelligence/warranty/foundation/object/source regressions. After tightening normalized quotation length, the final policy suite passed **34 tests** (overlaps the broad run; do not add counts). Tests include immutable revision/history preservation, incomplete clauses, citations/blank/short quotes, source kind/module/hash and owner scope, invalid values, stale bases, request-key reuse, concurrent identical writers, explicit invoice/date basis, boundary/difference/unknown-end behavior, no network, historical disconnection and unchanged input rows.
- Actual HTTP checks cover session/origin/no-store, malformed/extra bodies, policy source intake, idempotent policy save/get/list, saved graph comparison and foreign-policy rejection. The HTTP test correctly excludes request-specific transport correlation IDs from immutable-document equality.
- Final frontend/API-proxy/auth/domain suite: **215 passed in 34 files**. Covers guided cited save with stable retry, null unknowns, historical inspection/new revision, viewer restrictions, explicit comparison inputs/timezone, input/version stale-result discard, empty library and preserving source metadata in exports.
- TypeScript, ESLint and Next.js 16.4.3 production build passed on final source.
- Final Playwright: **14 passed** on desktop/mobile, including guided creation of all cited policy clauses, source inspection, immutable revision display/download, explicit saved complaint/policy/time selection, candidate date/scope result, report JSON checks and stale-result clearing, plus all earlier ontology flows. No page errors, page-level horizontal overflow or legacy writes. Policy and comparison export values were checked; no model call is made by either feature. Populated policies remain synthetic fixtures.
- Browser verification exposed policy dropdown names containing option text. Added explicit accessible names and a regression; modern browser pattern syntax was corrected. A test-fixture JSON-module import issue was fixed by keeping the synthetic fixture in TypeScript. Final browser flows pass without selector workarounds or weakened assertions. Source metadata preservation in exports has its own regression. Final `frontend/test-results/business-policy-library-*.png` and `business-policy-comparison-*.png` were visually inspected: phone layout, explicit review status, date/time/offset fields, policy cards and source/citation details are readable.
- Shared execution contracts and strict scoped OpenSpec valid; `git diff --check` passed. Original tracked Semantic Intelligence component/tests have no diff. Existing unrelated dirty work is retained.

## Offline actual-evidence boundary

`scripts/check_business_policy_evidence.py` opened the prior three private graph stores with SQLite mode=ro, validated owned saved graph/version evidence and inspected existing policy documents/tables without initializing policy state. All three had **zero owned Warranty policy documents and zero saved policy revisions**. The ticket graph contains two complaints; invoice and QA graphs contain none. Thus no real policy comparison was run and no authoritative policy or eligibility conclusion was fabricated. This describes saved evidence availability, not a new search of company systems.

Private summaries: `.local/business-ontology/chunk9-chunk6-connector-check/report.json`, `chunk9-chunk6-ticket-check/report.json`, `chunk9-chunk6-quality-valid-anchor/report.json`. Input file hashes stayed unchanged; comparisons/company queries/company writes/model calls/input-store writes all zero. Populated policy tests are explicitly synthetic fixtures and are not Simpson business evidence.

## Completion boundary

Chunk 9 is complete locally, not deployed, for draft intake and candidate scope/date comparisons. It does not establish complete authoritative policy, verified policy-to-identifier mappings, physical-engine identity, structured executable exclusion handling or final warranty eligibility. Monitoring/incorporation/confirmed-failure/exposure/population and production competency acceptance remain open. No new OpenAI transfer, company change, connector configuration change, live Business Ontology initialization, live service restart, deployment, SME approval gate or shared execution-contract change.

# Chunk 10 verification — 2026-11-01

## Delivered

- Identified and corrected a real namespace mismatch using supplied model declarations: invoice `oem` references OEM company, ticket `oem` references OEM account, ticket `oemOrg` references company and account `oemNameId` references company. Warranty input readiness v2 compares invoice company against ticket company, preserving both account/company observations. Existing policy-draft v1 literal account scopes are not silently reinterpreted.
- Versioned exact supplied-model quotes/hashes in `ontology/business-reference/identity-basis.json`. The declared `(oem, engineSerialNumber)` invoice uniqueness is recorded as archive evidence only; deployed indexes and physical identity are not asserted.
- New source graph mapping v2 preserves native identifier tokens inside hashed field evidence and annotates direct source fields. One bounded company lookup combines/deduplicates typed ticket, invoice and account company values; clipped twenty-value search domains and returned-row truncation remain visible. Added same-source account/company and invoice/company reference checks. Existing time/row/result/authority bounds and immutable older snapshots remain intact.
- Explicit saved-ticket resolver checks source record/field integrity and allowlisted same-source paths, keeps legacy type uncertainty, rejects malformed tokens/unsupported edge fields, exposes company-path conflicts and separate invoice/manual/SAP/QA candidates, and retains replacement dispatch serials as distinct observations. A unique scoped invoice stays a candidate; no auto-selection, physical-engine merge, identity table or eligibility execution.
- Scoped read-only/no-store association POST, selected-case UI, source/identifier inspection, company/candidate/reference/replacement detail, stale-result clearing and JSON export. Viewers may resolve owned historical evidence; no automatic resolution, company/model call or source/identity mutation.

## Verification

- Initial focused identity/graph/warranty checks: 78 passed. After adding HTTP/token/historical evidence checks, identity/warranty checks passed 60 tests (overlapping). Final broad backend suite: **311 passed**, covering all Business Ontology/generation/compiler/rules/graph/reference/intelligence/warranty/policy/identity/foundation/object/source regressions. Includes a direct regression that an invoice company equal to the ticket account is not a company-scope match, typed identifier collisions, multiple invoices, company conflicts, replacement separation, domain clipping, legacy snapshots and actual HTTP/scope/no-write checks. Existing deprecation warnings only.
- Final frontend/API-proxy/auth/domain suite: **219 passed in 35 files**. Tests verify explicit selection/action, no invented case on empty-ticket graphs, separate cross-source candidates, source inspection, late-result discard and explicit safe retry.
- TypeScript, ESLint and Next.js 16.4.3 production build passed.
- Final Playwright: **14 passed**, desktop/mobile association selection/run/source inspection, unresolved candidate rendering, JSON export checked for zero merges/company/model calls, selection-change clearing, plus all existing graph/policy/warranty/intelligence/reference/rules/compiler/generation/Simpson foundation/original Ontology flows. Zero page errors, page-level horizontal overflow or legacy writes. Final `frontend/test-results/business-associations-{desktop,mobile}.png` visually inspected; review status and candidate/evidence cards remain readable. Browser records are synthetic fixtures.
- Shared execution contracts and strict scoped OpenSpec valid; `git diff --check` passed. Original tracked Semantic Intelligence component/tests have no diff. Unrelated dirty work retained.

## Offline real-snapshot evidence

`scripts/check_business_associations.py` opens the owned earlier graph/version in SQLite mode=ro, validates saved records, resolves each saved ticket and writes a fresh private report directory. It loads no connector credentials or live application services and verifies input-store file hashes.

- Earlier ticket graph: two complaints, each with **two retained saved reference associations**, zero saved invoice candidates and unresolved physical-engine identity. Native-checked associations correctly **zero** because v1 snapshots lack retained identifier tokens. Legacy edges remain labelled saved-reference/unverified-types; no values were normalized into new identity facts.
- Earlier invoice-only and QA graphs: zero saved tickets, zero invented cases.
- All input file hashes unchanged; company queries/writes, model calls, input-store writes and identity merges zero. No new real source graph or deployed index enforcement is claimed.
- Private summaries: `.local/business-ontology/chunk10-chunk6-connector-check/report.json`, `chunk10-chunk6-ticket-check/report.json`, `chunk10-chunk6-quality-valid-anchor/report.json`.

## Completion boundary

Chunk 10 is complete locally, not deployed, for typed record-reference resolution and candidate/conflict handling, not confirmation of physical-engine identities absent from source evidence. Authoritative crosswalk/stable identity and replacement/history evidence are still needed, alongside authoritative warranty policy/exclusion input and monitoring/production evidence. The corresponding data-dependent tasks remain open. No SME workflow, company record change, external model transfer, live ontology initialization, service restart, deployment or shared execution-contract change.

# Chunk 11 verification — 2026-11-01

## Delivered

- Deterministic three-outcome warranty kernel with unknown precedence. Missing authority/applicability, physical identity or required evidence always requires review, including alongside failed limits. Trusted complete synthetic prerequisites exercise eligible and not-eligible outcomes. Public requests cannot supply verification flags, hours, policy overrides or exclusion findings. Current drafts/identity remain unverified/unresolved, so current application assessments never approve or deny a claim.
- Policy schema v2 adds seven nullable exact-source-cited calculation interpretations to the original twelve clauses: coverage mode, assessment-date basis, month calculation, separate period/hour boundaries, exclusion mode and required check codes. New saves require all nineteen keys; legacy immutable revisions remain readable without new defaults. Exact quotations establish provenance only. Required exclusions without verified mapped findings remain unknown; raw flags/text are not executed.
- Explicit saved-case calculations preserve primary complaint hours including zero and use decimal arithmetic. Selected sale/invoice periods apply declared calendar-month difference or clamped anniversaries with explicit equality boundaries. Leap years, month ends, zero months, reversed chronology and calendar overflow are handled. No implicit invoice, alternate hours, current-date fallback or failure-date basis is inferred. Draft arithmetic and final classification are separate.
- Scoped reader/no-store assessment POST accepts exactly policy ID (nullable), saved ticket, explicit timezone-qualified assessment timestamp and optional saved invoice. Missing policy returns Requires Review and null policy/source evidence without seeding a policy. Saved graph/version/policy/association integrity and owner scope are preserved. No new assessment table, company/model call, eligibility write or SME workflow.
- Explicit assessment action reuses the comparison form, supporting empty policy libraries, source inspection, check/blocker explanations, quotes, provenance and JSON export. Every input/version change clears prior results and discards late responses. Existing preparation, policy comparisons and original ontology remain available independently.

## Verification evidence

- Focused assessment/policy suite: 74 passed before the additional missing-policy HTTP assertions. Final broad backend suite: **351 passed**, including the additional HTTP assertions and all prior affected ontology/source regressions. Existing deprecation warnings only. Coverage includes all three kernel outcomes, individual verification gates, unknown precedence, zero/equality, anniversary/leap/month-difference/overflow cases, legacy drafts, exclusion contradictions, override rejection, foreign scope, historical disconnection, no network and unchanged saved table rows. Actual HTTP covers authentication/origin/no-store, selected/null policy, malformed input and foreign owner.
- Final frontend/API-proxy/auth/domain suite: **224 passed in 36 files**. Assessment tests cover explicit requests, separate draft/final states, safe errors, stale graph results, missing policy and rejection of positive/negative final classifications with unverified evidence.
- TypeScript, ESLint and Next.js 16.4.3 production build passed. Shared execution contracts and strict scoped OpenSpec valid; diagnostic/module Python compilation and `git diff --check` passed.
- Final Playwright: **14 passed**, including desktop/mobile cited schema-v2 policy creation, explicit saved assessment, unknown exclusions, JSON export fields, null-policy review and stale-result clearing; all earlier ontology flows also pass. Browser records/policies are synthetic. Zero page errors, horizontal overflow or legacy writes. Final `business-warranty-assessment-{desktop,mobile}.png` screenshots visually inspected: review status, blockers, check cards and export remain readable.
- Original tracked Semantic Intelligence component/tests and shared execution contracts have no diff. Existing unrelated dirty work is preserved.

## Offline actual-snapshot evidence

`scripts/check_business_assessment.py` opens explicitly owned earlier private SQLite graph stores in mode=ro, checks saved graph/version integrity and requires an explicit diagnostic timestamp. It does not load connector credentials or initialize policy tables. Selected timestamp `2026-11-01T12:00:00+05:30` is a diagnostic input, not a verified complaint/failure date.

- Real saved ticket graph: **two independent Requires Review cases**, each with null policy, incomplete evidence, POLICY_MISSING and unresolved physical identity. No fabricated policy or coverage arithmetic.
- Real invoice-only and two-source QA snapshots: zero tickets, zero invented cases.
- All input-store file hashes unchanged; company queries/writes, model calls and input-store writes zero; eligibility_final false.
- Private summaries: `.local/business-ontology/chunk11-chunk6-{connector-check,ticket-check,quality-valid-anchor}/report.json`. These are saved-evidence checks, not a fresh company-policy search.

## Completion boundary

Chunk 11 is complete locally, not deployed, for deterministic draft assessment and the gated decision kernel. It does not establish authoritative Simpson policy, verified physical-engine/applicability mapping or executable exclusion evidence. Those data-dependent tasks remain open alongside monitoring/incorporation/confirmed-failure/exposure/population and production competency acceptance. No deployment, live workspace initialization, service restart, source configuration change, company record change, additional OpenAI transfer, SME approval workflow or shared execution-contract change.

# Chunk 12 verification — 2026-11-01

## Delivered

- Explicit monitoring evidence report over one owned immutable graph, optional supported saved cut-in/QA/CAPA change, inclusive start/end calendar dates and bounded observation page. Reports preserve records/roles/connections/field states/hashes, date precision and direct/candidate association qualifications. Selected change is inspected separately; other records are not declared cohort members.
- Source-qualified identity, change, claim/inspection date/findings and primary complaint/claim hour observations. Failure-date buckets are source-field observations before/within/after the selected period, invalid or unavailable. Multiple claims/inspection records are never deduplicated into confirmed failures or summed as a numerator. No serial ordering, current-date fallback, alternate-hour substitution or POST_CUT_IN/approval interpretation.
- Eight prerequisite cards: physical identity, scoped applicability, actual incorporation, confirmed comparable failures, eligible population, longitudinal exposure, observation coverage and declared window. Usable observations remain unverified. Bounded source completeness does not establish population/follow-up completeness; individual hours do not establish exposure. Recurrence/rate/effectiveness/population/exposure metrics remain null with explanations.
- Scoped reader/no-store POST with exact inputs, strict valid/reversed-date checks, supported change selection, bounded integer pages, owner/version/record integrity and safe foreign/override rejection. Historical reports work after connector disconnection. No new monitoring table, company/model call, source mutation, alerts or schedule.
- Dedicated graph-view panel with explicit selection/date/run, prerequisite explanations, source inspection, paging, exact-page JSON exports, errors/retry and stale-result discard on every input/version change. Existing ontology, warranty/identity and intelligence features remain independent.

## Validation

- Focused monitoring backend suite passed 23 tests before the final selected-change HTTP assertions. Final affected backend regressions: **374 passed in two disjoint groups (125 + 249)**, including final selected-change HTTP assertions. The initial long combined process terminated with exit 143 before completion; its partial dots were not counted as a passing run. Both replacement groups finished with exit 0 and existing deprecation warnings only. Coverage includes explicit null/selected change, inclusive boundaries, timezone-preserved calendar dates/local precision, invalid/missing dates, zero recorded hours, raw statuses/potential causes, separate source roles/candidates, pages, empty and complete-looking snapshots, foreign scope, integrity, historical disconnection and unchanged rows. HTTP checks session/origin/no-store, malformed/extra inputs, selected change and foreign ownership.
- Frontend/API-proxy/auth/domain suite: **229 passed in 37 files**. Five monitoring tests cover explicit dates/action, null/selected change, reversed windows, paging/error handling, stale graph/input clearing and response rejection for invented metrics/confirmed states. The final fixture aligns manual-claim observations with the existing mapped reason field.
- TypeScript, ESLint and Next.js 16.4.3 production build passed. Shared execution contracts and strict scoped OpenSpec valid; diagnostic/module Python compilation and diff integrity passed.
- Playwright: **14 passed** across desktop/mobile, including monitoring run, null metrics/review state, source inspection, checked JSON page export and input-change clearing, plus all prior ontology flows. Synthetic browser records/policies remain clearly fixture evidence. No page errors, page-level horizontal overflow or legacy writes. `business-monitoring-{desktop,mobile}.png` visually inspected: explicit dates, unavailable metrics, prerequisite cards and mobile layout are readable.
- Original tracked Semantic Intelligence component/tests and shared execution contracts have no diff. Unrelated dirty work is preserved.

## Actual saved-snapshot evidence

`scripts/check_business_monitoring.py` reads explicitly owned previous private SQLite stores in mode=ro, traverses all report pages, requires explicit diagnostic dates, supports explicit saved change selection and verifies input-file hashes. No credentials or live services are loaded. The entered 2026 calendar window is diagnostic, not an established monitoring cohort/period.

| Earlier real saved graph | Records | Monitoring observations | Saved change candidates | Failure-date observations |
| --- | --- | --- | --- | --- |
| Invoice-only | 1 | 5 | 0 | 0 |
| Ticket | 4 | 12 | 0 | 0 |
| Invoice/QA | 2 | 15 | 1 | 0 |

All metrics remained null, status requires_evidence. Explicitly selecting the real saved QA record exposed applicability observations as observed_unverified; incorporation/comparable failures/population/exposure remained unavailable. Zero failure-date observations does not establish zero failures or absence from company systems. Every input file hash stayed unchanged; company queries/writes, model calls, input-store writes and schedules zero.

Private summaries: `.local/business-ontology/chunk12-chunk6-{connector-check,ticket-check,quality-valid-anchor}/report.json` and `chunk12-qa-selected-change/report.json`. No fresh company-wide population or policy search is claimed.

## Completion boundary

Chunk 12 is complete locally, not deployed, for monitoring evidence and prerequisites. A fully populated reliability program and confirmed recurrence/rate/effectiveness calculation still require the evidence below. Authoritative identity, scoped incorporation/change applicability, comparable confirmed failures, cohort and longitudinal exposure mappings remain open data dependencies, alongside actual warranty authority/exclusions and production competency/deployment acceptance. No deployment, live ontology initialization, service restart, source configuration change, company record change, extra OpenAI transfer, SME gate or shared execution-contract change.


# Chunk 13 verification — 2026-11-01

## Delivered

- Explicit offline owner/workspace-scoped SQLite release audit with a consistent read-only snapshot, fixed ten-table/column allowlist, unknown-schema rejection and 2,000-row/table plus 64 MiB selected-row bounds. Input file hashing streams in chunks. Connector/credential tables, encryption keys, other owners and environment files are excluded.
- Fresh private ontology-artifact recovery database with fixed known schemas, primary/unique keys and the one-active-generation-job partial unique index. Immutable document and job contents are preserved; original/recovered owned snapshot hashes and recomputed monitoring reports must match. No application or worker starts and no queued/uncertain model job replays. A second owned snapshot and input file hash verify unchanged inputs.
- Source document, draft, graph/version/projected field, policy document/head/history and compilation input/export/report integrity checks. Missing/duplicate compilation exports and mismatched validation JSON fail. Saved definition/instance validation states remain visible; recovery integrity does not establish business correctness or full instance coverage.
- Current working-tree code/reference/test/docs file hashes, Git commit/dirty state and installed dependency inventory. This identifies inspected bytes, not a committed release bundle, frontend build attestation or vulnerability scan.
- All 22 exact blueprint competency questions/prerequisites with inspection-tool support and implementation gaps, consistently not_accepted. The reviewable matrix explicitly records assessment-date versus failure-date coverage, bounded claim population, unverified statuses/findings, identity, incorporation, exposure and comparable cost/currency limitations.
- Current production authentication admission is probed via local security code only. It remains blocked_by_current_code; public_release_status stays not_ready. Live HTTPS/individual-role acceptance, production workers, full credential/key-backed application recovery and target storage acceptance remain not_run. CLI exits 2 for a completed not-ready audit and 1 for unavailable/integrity failure.
- Concrete release/rollback runbook with target, authentication, complete recovery, staging, worker interruption and business acceptance steps. No service promotion, restart, auth/config change or deployment action is performed.

## Verification

- Related release/security/compiler/monitoring/policy run: **115 passed** (includes an earlier 14 audit tests). After final bounds/schema/export/history strengthening, final audit suite: **16 passed**. These counts overlap and are not added. Existing deprecation warnings only.
- Audit tests cover owned recovery/hash/report equality; foreign data exclusion; private permissions; no source/model calls/input mutation; policy history and queued/running jobs independently; restored active-job uniqueness; corrupt source/version/graph/compilation/policy rejection; empty export and torn head rejection; schema/row bounds; no overwrite; recovery tampering/input drift; all 22 non-acceptances; source hashes; CLI exits 2/1.
- Existing production security regressions confirm production mode fails closed and remote/cross-origin development sessions are rejected. No production login was implemented or bypassed.
- Shared execution contracts, strict scoped OpenSpec, Python compilation and diff integrity passed. Frontend/product runtime code was unchanged in this chunk, so chunk-12 frontend/build/browser checks remain prior evidence, not freshly repeated or claimed as live acceptance. Unrelated dirty work is retained.

## Actual saved-snapshot audit

The earlier invoice/ticket/QA private stores were opened read-only. Each contained one saved draft/compilation and one graph with respectively one/four/two source records. Compilation status was passed; instance validation was passed/not_run/passed respectively, preserving the ticket graph's zero-mapped-record limitation. All had zero policy revisions and zero accepted business competencies. Artifact recovery and recomputed monitoring hashes matched, while public production readiness stayed not_ready. No zero failure/rate or verified policy conclusion was invented.

Final private evidence: `.local/business-ontology/chunk13-final-{connector-check,ticket-check,quality-valid-anchor}/report.json` and their separate `ontology-artifacts.sqlite3` recovery databases. These contain owned ontology artifacts only and must remain offline. Input file/snapshot hashes unchanged; company queries/writes, model calls, input writes and services started zero. Diagnostic dates are explicit test inputs, not an established monitoring period.

## Completion boundary

Chunk 13 is complete locally for release audit, competency-gap review and recovery/deployment preparation. It is not public-production acceptance, a full application disaster-recovery test, deployment or completion of all original business semantics. Current trusted production login is deferred in code; authoritative policy/exclusion, physical identity/applicability, incorporation/comparable failure/cohort/exposure and complete module competency evidence remain open. The unchecked data-dependent tasks are retained. No live initialization, service restart, credential/environment change, new model transfer, SME validation interface or shared execution-contract change.


# Chunk 14 verification — 2026-11-01

## Authorization and scope

The owner explicitly deferred individual login and requested step 3 backup/recovery and step 4 activation to inspect the working Business Ontology tab. The existing shared-workspace deployment was updated without changing authentication, origins, private listeners or production-mode admission. This is functional activation, not completion of individual-user production login or all business semantics.

## Full application recovery check

Private evidence/backup root: `.local/business-ontology/live-rollout-20261101/`, mode 0700. A consistent full SQLite application backup contains 83 application tables. Three supporting SQLite databases and their non-database artifacts, fifteen required configuration/service/key files, working-tree runtime source archive, tracked patch and preceding frontend artifacts were retained privately. Historical/test/backup directories in the 121 GiB `.local` tree were deliberately excluded from recursive copying.

Private restored copies matched backup file hashes and passed SQLite integrity checks. Backed-up encryption configuration decrypted both source connector credentials and four stored Google credential records in memory. Restored original ontology, uninitialized Business Ontology and policy-library API reads passed with workers/network disabled. Three original ontology versions remained. The restored API test used the application's expected root-path dev-session cookie; no credential/authentication setting changed. Supporting databases are individually consistent snapshots, not an asserted distributed snapshot; no off-host/external-provider recovery is claimed.

## Activation

- Isolated frontend production build (Next.js 16.4.3) passed after supplying the existing sibling shared-contract directory required by the staged layout. Exact staged artifact passed **14 desktop/mobile browser flows** before activation. No application implementation fix was necessary for staging.
- Active build: **Bl1WZvbmZJ-iK9fyeGHGt**. Retained 67 preceding static files for existing browser references. Atomically moved the tested artifact while stopping only the Builder frontend; preserved `active-before.next` and `backup/previous.next`.
- Checked planning/generation/query/lifecycle/runtime queued/running work: zero before activation. Restarted only Builder backend, worker and frontend. All active; backend/UI remain loopback-only on ports 8002/3001. One current worker is active; 54 historical stale registrations remain retained. Generation integration reports configured=true and zero jobs submitted by the rollout; no paid live generation was tested.
- Original live backend Business Ontology endpoint returned 404 before restart, and returned real owned state afterwards. Initialized only the separate Business Ontology with the two existing Simpson source IDs. Added source-cited curated reference drafts across all twelve modules: **67 concepts, 14 relationships, 3 non-executable candidate rules**. Compilation passed. Reference drafts are not fresh model generation or verified policies.

## Actual live source/API verification

- Complaint graph: **4 service records, 2 separate complaints**, two mapped records, instance validation passed. Association resolution retains unresolved physical identity. Readiness/assessment/intelligence APIs passed; missing policy returns Requires Review with null policy evidence. No real policy was seeded.
- Invoice/QA graph: **3 records (2 service, 1 quality)**, one candidate edge, instance validation passed. Cross-source candidates remain separate; no confirmed identity or recurrence invented.
- Monitoring readiness passed with explicit diagnostic dates; unsupported recurrence/rates/effectiveness remain unavailable. Exact live payloads passed the shipped frontend root/version/graph schemas.
- Original ontology record and version payloads are unchanged: **416 records, 3 versions**. Source credential ciphertexts and backed-up configuration files unchanged. Graph builds are bounded read-only company queries; no company write or model call occurred in the verification actions.

## Actual HTTPS browser verification

Both desktop and **390px mobile** passed through the normal shared-workspace login on the actual HTTPS site and real backend. Verified live Business Ontology overview, saved graph selection/record count, warranty preparation, missing-policy assessment, downloaded JSON values, monitoring readiness and switching back to the original ontology graph. Zero page errors, unexpected/blocked mutations and page-level horizontal overflow. Live smoke selectors were aligned with existing wrapped dropdown/current graph labels; no product code change. Final overview/monitoring screenshots visually inspected.

Private evidence: `restore-report.json`, `activation-plan.json`, `initialization-report.json`, `live-api-report.json`, `live-quality-report.json`, `live-browser-report.json`, `deployment-report.json`, worker status and screenshots under the rollout root. Shared contracts, strict scoped OpenSpec and diff integrity passed.

## Result and remaining boundaries

The requested shared-workspace functional rollout is active at https://praxi.bellcorpstudio.com/app/data-intelligence → Business Ontology. Both source bindings, references, saved graphs and read-only report flows are available to inspect now. Individual login remains deferred by the owner. Authoritative warranty/identity/exclusion and monitoring/competency evidence remain data dependencies, so unavailable decisions are not fabricated. Full rollback details and the limitations of pre-activation working-tree source reconstruction are documented in `docs/simpson-business-ontology/functional-rollout.md`. No original ontology reset, connector configuration change, SME gate, email/workflow invocation or new OpenAI transfer was part of this rollout.

## Chunk 15 — three reference rules executed and deployed (1 November 2026)

The owner explicitly requested completion after finding that the three displayed reference rules were definition-only. This follow-up implements their execution rather than relabelling the old safeguards as complete. It adds fixed semantic-definition-matched handlers, an evidence source kind, immutable scoped/cited input revisions with optimistic concurrency and retry keys, four API routes, a source/evidence editor and history, explicit runner, check explanations, source-qualified results and exports. See [rule execution](../../../docs/simpson-business-ontology/rule-execution.md) for actual inputs, outcomes, examples, formulas and boundaries. No SME gate or new login was added.

Root-cause execution distinguishes similarity/inconclusive hypotheses, documented inspection/test diagnoses, ruled-out causes and unknowns. Recurrence executes applicability, actual incorporation, same-engine linkage, mechanism/root-cause/investigation comparison, chronology and explicitly supplied exposure conditions. Rate execution requires a defined complete cohort/period, distinct confirmed first-failure numerator and positive population/exposure; invalid conditions and missing evidence have different outcomes. Exact decimal calculations include valid documented zero failures. These checks consume explicitly cited source assertions; neither citations nor manager entry independently verify truth. No cause, threshold, date, physical identity, denominator or company business decision is invented.

### Validation

- Backend: **330 passed** across all fifteen `tests/test_business_*.py` files, in three bounded runs: foundations 102, consumers 181, execution/recovery 47. Execution tests include complete/negative/unknown paths, decimal/zero boundaries, exact-definition dispatch, ownership, typed inputs/citations, history/concurrency/idempotency, HTTP/session/origin errors and recovery. Existing FastAPI lifecycle deprecation warnings remain.
- Relevant frontend: **233 passed, 38 files**, covering data-source screens, API proxy, workspace auth and domain logic. Types and lint passed. The final compilation wording adjustment additionally passed its five existing unit tests.
- Broader frontend diagnostic: 352 passed, three failed in unchanged `src/api/phase4-journey.test.tsx`. Failures concern closed lifecycle detail visibility and missing ResizeObserver in the workflow graph test environment. They are outside this rule change; no claim that the entire frontend test suite is green is made. Private `frontend-tests.log` retains the errors.
- Staged build `gl8vdk6t4hijeGGHnE9tg`: **16 desktop/mobile browser tests passed**, including every evidence form, source intake, all three missing/complete rule paths, saved history, checked JSON downloads and the existing original ontology lifecycle. Test example: 5 failures / 100 engines / 10,000 at-risk hours yields 5.000000% and 0.500000 per 1,000 hours. Synthetic assertions are confined to test fixtures.
- A late display review found the compilation panel's old blanket “candidate rules are not executable” sentence. It now describes definition-only compilation and directs users to handler availability and the saved-graph runner. Final build **`a7IU7JeJHO8dSVuERAul2`** passed build/types and four relevant desktop/mobile compilation/rule flows before activation. No handler logic changed in that adjustment.
- Shared contracts and strict scoped OpenSpec validation passed; diff whitespace check passed. No new OpenAI smoke test or paid request was made.

An initial browser-server launch encountered contention while importing the app's default database. The browser suite was rerun with an explicit private `BUILDER_DATABASE_URL` for bootstrap as well as a fresh isolated fixture store. Default app imports can initialize additive tables; no assertion that tests left every byte of the live application database unchanged is made. Business/original-ontology/source preservation was checked independently below. Early browser request-list omissions were corrected to include ordinary workspace reads; they did not hide mutating requests or alter application behavior.

### Backup, activation and actual live evidence

Private root: `.local/business-ontology/rule-execution-rollout-20261101/` (0700). Fresh consistent backup: four SQLite databases, 86 application tables and 15 private configuration/key/service files, with integrity and hashes recorded in `backup/manifest.json`. Source archives and frontend rollback artifacts are retained. The earlier whole-application restored-key/read verification remains in the chunk-14 recovery evidence; this follow-up separately tested restoration of all three saved evidence revisions, source/hash preservation, and rejection of torn heads, missing graphs and mismatched series. The recovery schema now includes the two rule-evidence tables (twelve scoped artifact tables total). Fresh backup integrity does not claim a new off-host recovery drill.

Checked planning/generation/query/lifecycle/run queues had zero active work before activation. Only existing Builder services were restarted, preserving authentication, environment, listeners and credentials. The final wording correction restarted only the frontend. The initial activation retained 88 old static files and the final artifact additionally retained 91 missing static assets. `active-before.next` retains the pre-rule frontend; `before-copy-correction.next` retains the intermediate build. Rollback must preserve later application data and additive evidence tables.

The actual HTTPS application at `https://praxi.bellcorpstudio.com/app/data-intelligence` passed desktop and 390px mobile checks through the existing shared login and real backend on the final artifact: all three handlers available, explicit execution, source-qualified missing-evidence checks, checked downloaded results, evidence-editor availability, stale-result clearing, corrected compilation text and original ontology navigation. Zero page errors, unexpected mutations or page overflow. Live screenshots were visually inspected. Separate API checks ran all three rules against both saved genuine graphs: six successful executions, all honestly `insufficient_evidence` because no supporting case/cohort input revision has yet been supplied. Every result reports `rules_executed: true`, zero model/company-query/source-write counts and handler/input provenance.

Preservation compared actual stored data, excluding transport-generated correlation IDs: **416 original ontology records and three versions unchanged**; selected immutable Business Ontology definition, both saved graph documents and encrypted source credentials unchanged. Private configuration hashes still match the backup. No synthetic source/evidence revision was saved in the live workspace, no policy was seeded, and no source record, workflow, email or other provider write was performed.

The three displayed reference-rule execution paths are complete and live. This does not accept all 22 blueprint business competencies or independently verify missing company evidence. Individual production login remains deferred as requested. The existing monitoring-readiness view continues to report what the bounded graph itself establishes; the new rule runner evaluates additionally supplied cited inputs.

Private receipts: `backend-{execution,foundations,consumers}.log`, `frontend-scoped.log`, `browser.log`, `browser-final.log`, `build-final.log`, `activation-report.json`, `live-api-report.json`, `original-comparison.json`, `live-browser-report.json`, screenshots, backup manifest and final source archive. Company payloads/credentials remain out of public documentation.

## Generation controls follow-up — deployed 1 November 2026

Owner request: fix the generation/source buttons and confusing display of two engine successes beside an older organization failure. Implemented selected-module latest result cards, exact-revision/module **View generated draft** navigation (including after a historical version selection), explicit status refresh, separate expandable run history, failed-attempt retry and clear source import/save feedback. Source inspection reads its saved document with module scope. Polling no longer repeatedly fetches the whole workspace for an already synchronized completed job. No failed job is relabelled as a success or erased.

Reproduced a regeneration context omission: retained definitions can refer to target-module concept IDs, but those required target concepts were not supplied to the model. The payload now includes dependency-required concepts with their existing meaning/evidence, the prompt requires those IDs, and validation rejects dropped dependencies with an actionable allowlisted diagnostic. Exact citations, identifier/basis checks, cycles and reference integrity remain enforced. The configured model/API/output schema and no automatic provider retry are unchanged. Prompt version `simpson-evidence-v2`. The old organization job retained only a generic invalid-result error, so no claim is made that this context defect was its exact historical cause. See the official OpenAI guidance linked in extraction-api.md; strict structured output does not replace application semantic checks.

Validation: **62 backend tests passed** (generation, reference import, rule execution); **236 frontend tests in 38 files passed** (data sources, proxy, workspace auth and domain); types, lint, production build, shared contracts, strict scoped OpenSpec and diff whitespace passed. New meaningful tests cover dependency-preserving regeneration, useful failed validation without application changes, exact-draft navigation, isolated history, source feedback, explicit retry and no repeated synchronization. Eight desktop/mobile browser checks passed, exercising actual control handlers for import, source read/add, generation, cancellation, status refresh, latest/historical version navigation and existing reference/rule workflows against isolated fixtures. Tests used private bootstrap and fixture databases and made no model/provider call.

Read-only local validation additionally checked the current saved definitions for **all twelve modules** against their current owned source documents and saved schema context: all passed. This validates existing drafts, not twelve new model generations or independently verified business meaning. Private `saved-module-validation.json` records this distinction.

Final active frontend **`8vqaj-Sh-UmNStQEmrsVU`**. A fresh consistent private backup covers four SQLite databases (86 application tables) and 15 configuration/key/service files. Queues/runs were checked inactive before restarting only existing Builder services; authentication, configured model, environment and listener ports remained unchanged. Frontend rollback is `active-before.next` under `.local/business-ontology/generation-controls-20261101/`; 111 older missing static assets were retained. Existing source versions and job history were preserved, with no migration, forced regeneration, fake completed job or replacement of company evidence.

Actual final-build HTTPS desktop and 390px mobile verification passed through the existing login and real backend: latest engine draft **revision 4**, historical **revision 3**, source read, idempotent reference import, status refresh, source-form display and organization retry availability. No generation, source-document save or job cancellation was submitted live. Zero browser errors, blocked/unexpected mutations or page-level overflow. One initial live test checked the selected version before React finished updating; replacing the immediate assertion with an awaited locator assertion passed without changing product code. Screenshots were visually inspected.

Preservation compares raw owned table contents with the fresh backup: one workspace, four versions, 24 source documents, two graphs and three jobs unchanged, with empty policy/evidence revision tables unchanged. Separate existing-rule API regressions passed all six checks on both saved graphs. Original ontology still has **416 unchanged records and three unchanged versions**; source credential ciphertext/config hashes are unchanged. No company write, workflow/provider action, new paid model call or synthetic evidence seed occurred.

Private evidence root: `.local/business-ontology/generation-controls-20261101/`, containing `backend.log`, `frontend.log`, `types.log`, `lint.log`, `build.log`, `browser.log`, `saved-module-validation.json`, `backup/manifest.json`, `activation-report.json`, `live-browser-report.json`, `live-api-report.json`, `preservation.json` and screenshots. Individual production login remains deferred; the three unrelated broader workflow journey frontend-test failures recorded in chunk15 are outside this change and are not claimed fixed.

## Source-classification reliability — deployed 1 November 2026

The owner reported two new failed engine generations after the controls fix. Both stored errors identify the same specific cause: a policy/code-derived rule classification without a matching cited source kind. The earlier controls follow-up did not solve that content-path failure; this follow-up changes generation preparation itself.

Implemented dynamic provider JSON-schema basis choices from actual source kinds, plus deterministic conservative classification from each rule's actual cited sources before strict validation. Unsupported authority becomes proposed logic, never a promoted policy/code claim. A globally available but uncited policy/code document does not establish the rule's basis. All original validation gates remain. `validate_result` itself stays strict for saved-draft/compiler integrity checks; `prepare_result` performs generation-only correction. The raw provider response is not mutated. Adjustments are stored in job/version provenance and explained in the success card and version inspector. No extra model request, automatic retry, invented quotation, deleted rule, stale-draft fallback or mutation of historical failures.

Read-only current-source checks cover all twelve modules. There are no policy documents in their current generation context, so `policy_statement` is excluded for all twelve. Eleven modules, including engines, have supplied application-code sources; monitoring currently permits proposed logic only. Even where code is globally available, a rule citing only blueprint/schema evidence is kept proposed. Private `live-source-constraints.json` records these actual source kinds/choices without company-record reads or provider calls. Source origin/type alone still does not verify company policy semantics.

Validation: **41 generation tests passed**, plus **103 related compiler/rule/execution/recovery/reference tests** (144 distinct backend checks). Tests reproduce the engine policy-label failure, verify successful first-attempt persistence with exactly one fixture provider call, test policy/code presence versus actual citation, retained strict rejection, no input mutation, authority downgrade without text/citation changes, and genuine-invalid rejection. The initial combined run had 142 passes and one new test-fixture failure because its summary document lacked source text. That fixture was corrected to read the complete owned source; the entire generation suite passed afterward. No product failure was bypassed or assertion removed. Logs retain both results. Existing FastAPI deprecation warnings remain.

**237 frontend tests/38 files passed**, along with types, lint and production build. **Six desktop/mobile browser checks passed**, including successful generation with correction metadata visible, source actions, cancellation/history/navigation, unchanged compilation and all three rule executions. One provider submission was asserted for the successful generation fixture before its separate cancellation scenario. This is controlled provider-response testing, not a new real-model success or paid test claim. The official structured-output guidance linked in extraction-api.md informed the provider-enum constraint; schema adherence does not eliminate semantic validation.

Final active frontend **`gWzXNxEi87sxiMImvcTFs`**. Fresh backup: four SQLite files, 86 application tables, 15 private configuration/key/service copies with integrity/hashes. Queues were inactive before restarting only existing Builder services. Configured model, environment, shared login and loopback listeners unchanged; 132 missing old static assets retained. Private rollback: `.local/business-ontology/source-classification-20261101/active-before.next`. No paid generation, source document save or cancellation was submitted in the live workspace.

Actual final-build HTTPS desktop/mobile verification passed existing-source import/read, status, latest and historical engine revision navigation, history retention and retry/form availability with zero page errors or overflow. The four saved versions, 24 source documents, two graphs, all five jobs (including the actual failures) and empty policy/evidence revision tables compare unchanged with the fresh backup. Original ontology416 records/three versions, credential ciphertexts and private config hashes remain unchanged. Existing rule API checks on both saved graphs also passed. Live saved revision4 remains available; the fix applies to new generation requests, not invented replacement history. No company/provider write, workflow execution or additional model call.

Private evidence root: `.local/business-ontology/source-classification-20261101/`; receipts include `backend.log`, `generation-final.log`, `frontend.log`, `build.log`, `browser.log`, `live-source-constraints.json`, `backup/manifest.json`, `activation-report.json`, `live-api-report.json`, `live-browser-report.json`, `preservation.json`, screenshots and deployment summary. This completes the reported source-classification failure fix, not a universal guarantee that an external model/provider can never produce another error. Individual production login and the previously documented unrelated workflow journey test failures remain outside this change.

## Warranty knowledge and revision selection — deployed 1 November 2026

Owner reports the empty warranty-policy library and a glitch when choosing a revision, and asks what warranty answers would be based on. Confirmed zero saved written-policy interpretations despite an owned supplied warranty-code source with four explicit branches. Confirmed selector reset: the control used the loaded detail's ID while selection cleared that detail before asynchronous loading. This follow-up fixes both actual behavior paths.

Implemented `business_warranty_reference.py`: reviewed, hash-pinned source parsing for the four supplied branches; exact citations for invoice/sale/hour limits, calculation mode/month conventions and inclusive boundaries. Atomically/idempotently imports four implementation-derived drafts into the existing owner-scoped policy store with branch/selector/source-hash provenance and explicit descriptive basis. No inferred OEM account IDs, model scope, effectivity or exclusions. Source kind and final policy authority stay distinct. Source-code imports are accepted as code interpretations, never written policies; the previous source-kind test now asserts this distinction rather than requiring all code to be unusable. Other source/type/quote/revision/auth checks remain.

The library displays an immediately useful source-backed limit table, read-source actions and labelled draft revisions. It explains the evidence for code-limit questions and the remaining requirements for final contractual eligibility. The selector keeps a dedicated ID during loading and rejects stale results; empty selectors are disabled, edits/saves invalidate pending reads, and library changes refresh graph comparison choices through an explicit refresh token. Existing case preparation/assessment remains source-qualified and does not gain blanket eligibility authority.

Validation: **92 backend policy/assessment/recovery tests passed**. They include all four exact limit triples, unknown exclusion/effectivity/scope clauses, exact citations, source integrity, manager/owner/origin/HTTP checks, atomic rollback after a partial import, idempotent re-import, scoped recovery of all four revisions and Requires Review assessments without network/model calls. **239 scoped frontend tests/38 files passed**; an additional refresh-token case was then added and the full ten-test policy file passed (240 distinct scoped cases total). Types and lint passed. Final frontend build **`2ffYX6_wB2IeyuqzFrhrw`** passed. The test fixture required an explicit JSON import attribute for the Node browser runner; corrected without changing product behavior.

**Eight desktop/mobile browser checks passed**, including the new knowledge import, four rows/limits, a slow first revision response arriving after a second selection, stable selected values and detail, source reading, missing-exclusion display, checked JSON download and refresh. Existing source graph, generation/cancellation/history and all three rule-runner flows also passed. No model/company-source calls in tests. Shared contracts, strict scoped OpenSpec and whitespace validation passed.

Private root `.local/business-ontology/warranty-knowledge-20261101/`: fresh consistent backups of four SQLite databases (86 application tables) plus 15 configuration/key/service files, source archive and frontend rollback `active-before.next`. Confirmed no active work before restarting existing Builder services only. Model/environment/auth/ports unchanged; 154 old missing static assets retained. Individual production login remains deferred as requested.

After activation, explicitly imported the **real supplied source already owned by the live workspace**, creating four policy heads/revisions and four audit events. These are genuine source-cited code interpretations, not synthetic test records or invented policy documents. Read each revision back, checked its content/source hashes and all four exact triples, confirmed unknown scope/effectivity/exclusions and false verified/executable flags, and re-imported without changes. No written-policy document was added or claimed present. No model request, company read/write, workflow or provider action occurred.

Actual final-build HTTPS desktop/mobile checks through the existing login and real backend passed: four visible source-labelled branches, rapid stable revision selection, source text/provenance, verified downloads, refresh without reset, all four choices in saved-case comparison, and working comparison/assessment with honest Requires Review for incomplete evidence. Zero page errors/blocked unexpected mutations/overflow. Screenshots were visually inspected (the narrow table supports internal horizontal scrolling).

Preservation: owned workspace, **four ontology versions, 24 source documents, two saved graphs and five generation jobs unchanged**. Rule-evidence tables unchanged. Only the expected four policy heads, four policy revisions and four audit events were added. Original ontology remains **416 unchanged records/three versions**; source credential ciphertext/config hashes unchanged. Existing six rule executions across both source graphs passed their unchanged missing-evidence outcomes. The earlier unrelated broader workflow test failures are still outside scope and are not claimed fixed.

Evidence: `backend.log`, `frontend.log`, `frontend-final-targeted.log`, `types.log`, `lint.log`, `build.log`, `browser.log`, `live-import-report.json`, four `live-warranty-*.json` documents, `live-browser-report.json`, `live-api-report.json`, `preservation.json`, backup manifest, screenshots and deployment report. The completed scope is usable implementation-derived warranty knowledge and stable draft selection; it does not assert that absent written policy/exclusion/identity evidence has become known.
