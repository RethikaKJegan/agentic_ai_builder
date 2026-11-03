# Design

## Context

See proposal.md for motivation and the four capability specifications for acceptance behavior. Read-only inspection found:

- `data_source_adapters.py` supports Atlas MongoDB and Supabase PostgreSQL. Mongo discovers fields from at most 25 documents per collection. PostgreSQL discovery collects fields, constraints and indexes but does not calculate business-value profiles.
- `data_sources.py` persists snapshots and leased discovery jobs. `data_refresh.py` schedules periodic discovery with bounded backoff; it is not a change-stream or generalized incremental synchronization service.
- `data_relationships.py` generates structural and naming-based candidates. `data_graph_v2.py` adds entity mappings and conservative qualification; neither supplies calibrated probabilities.
- `data_ontology.py` and `semantic_kg.py` retain reviews and source-anchored semantic proposals. Semantic confidence deliberately remains null. Source changes can require renewed review.
- `kg_retrieval.py` retrieves bounded owned source context; its current projection can include inferred semantic relationships. It is not an approved layered ontology resolver.
- Frontend Data Intelligence has source/relationship review, record exploration and a structural EDA summary. The EDA summary does not calculate null rates or value distributions.
- Existing metadata and graph revision tracking does not establish immutable approved publication of concepts, constraints and mappings or complete correction-to-run dependency lineage.

The existing Simpsons connection is user-reported. Its active identity, source scope, coverage and business definitions still require bounded verification; no live source was queried during planning. Untracked technical-research documents predate this change and must be preserved.

## Goals / Non-Goals

Goals: extend existing persistence and authorization boundaries; separate structural evidence from business meaning; build all six sections of the user's specification; preserve auditable original proposals and reviewed history; provide honest incomplete states.

Scope clarification: implement only the six ontology subsections in user Section 1. Later product stages remain separate. Selection resolves ontology concepts/dependencies only. Replay is impact/eligibility plus existing authorized submission integration, not a recovery engine. Ordinary graph cycles are allowed; only explicitly acyclic relationship rules and redirect chains prohibit them.

Non-goals: replacing the workflow planner/runtime, new model training infrastructure, automatic correctness claims, broad source scans beyond configured authority, or automatic repetition of external writes. These boundaries do not remove the required ontology-to-workflow revalidation/replay integration.

## Decisions

### Durable typed graph over existing persistence

Add versioned concept, attribute, mapping, constraint, relationship, evidence and dependency records with indexed endpoints and scope keys. Keep durable stable IDs independent of names and revisions; retain immutable snapshots for publication. Use JSON payloads for bounded source-specific evidence with explicit schema validation. This fits existing SQLite/PostgreSQL storage adapters and permits export/traversal without adding a graph service. A separate graph database adds migration/operational cost without demonstrated need; revisit only if measured traversal limits demand it.

Every record carries workspace/owner scope under current ownership boundaries, layer, revision, status and provenance. Common/domain definitions can be reusable templates, but organization mappings and restricted evidence remain scoped. Cross-tenant evidence never becomes a shared template. Domain definitions cover Sales, Procurement, Finance and Customer Service; templates carry documented origins and are not asserted as Simpsons facts. Organization rules and approval hierarchies require source-backed or reviewed definitions.

### Catalogue and profiling jobs

Retain metadata jobs and add independently versioned bounded value-profile jobs with leases, generation fences, source revision and freshness. Enumerate connector capabilities explicitly. Compute summaries at source or within bounded local samples; persist summaries and evidence hashes instead of bulk source records. Record exact scope, basis, denominators, missing/unsupported metrics and truncation. Use type-safe normalization and composite-key handling for overlap/referential tests. Unauthorized profiling never falls back to wider credentials.

Mongo sampled absence is not deletion; PostgreSQL source OIDs or equivalent continuity evidence can support rename proposals, while ambiguous changes require review. Maintain a source-to-evidence dependency index. Incremental means only changed catalogue/ontology components are recomputed; a connector that must rescan metadata advertises that limitation honestly. Enterprise application/API connector support uses explicit capability contracts and bounded pagination/checkpoints; existing Google discovery is integrated only for the metadata it actually exposes.

### Evidence packages and assessment

Store immutable candidate generation output separately from normalized graph records. Evidence packages cite exact source fields, schema/profile revisions, methods, semantic definitions and contradictory signals. A structural FK, observed key match and a business predicate are separate assertions with separate validation states.

Assessment produces per-signal availability and scores plus a method version. Heuristic ranking is allowed but never labelled a probability. Start with explicit uncalibrated status until reviewed examples support a calibration artifact. Use a simple auditable empirical calibration mapping with held-out reviewed examples, minimum-support gates and precision uncertainty bounds. Keep evaluation splits grouped by source/relationship family to reduce leakage. Store sample counts, precision, correction/false-positive metrics and the acceptance policy. Low-risk automatic acceptance requires an approved applicable calibration and precision gate; otherwise route to review. Synthetic fixtures validate machinery but do not establish production calibration.

### Review and publication

Extend current inspectors with layer selection, definitions, attribute/constraint editing, conflicting evidence, impact summaries and a prioritized queue. Review actions include accept/reject/correct/merge with reason and optimistic concurrency. Preserve original output and all decisions as evaluation labels. Merge uses typed compatibility validation and redirect records, preserving old IDs and preventing cycles.

Draft authoring is separate from approved publication. Publication validates endpoint closure, rule/type consistency, current evidence and approval policy in one transaction, assigns an immutable version and records its source/calibration manifest. Unaffected approved mappings can be reused across versions by unchanged evidence hashes. Legacy suggestions import as drafts; existing reviews retain provenance and require current validation before entering the first approved publication. There is no silent bulk approval migration.

### Controlled access and task subsets

Introduce `/ontology/v1` endpoints for draft/review management, publication, versions, typed lookups, exports and bounded task resolution; `v1` identifies the API schema, while an explicit ontology version identifies content. Retain existing endpoints during migration. All routes use current identity/origin guards and enforce current source permissions at lookup, traversal and export. Unknown/revoked ownership fails closed. Existing tools.assign management access is the initial author gate; reusable ontology access helpers prevent per-endpoint inconsistencies.

Resolve seed concepts/source fields and bounded dependency closure across layers, then issue a manifest containing ontology version, concept/relationship/mapping IDs, evidence revisions, authorization scope and content hash. Missing required context returns an explicit incomplete result. Cache keys include these revisions and permissions; cached results are never an access grant. Downstream planning consumes approved manifests; unapproved candidates remain visible in review APIs only. Preserve separate technical join authorization and shared execution contracts.

### Correction impact and workflow integration

Register dependencies when planning pins ontology context and when runs consume it. Record the actual consumed manifest in run provenance. On corrected evidence/definitions, traverse the dependency index, invalidate affected cache entries and mark affected workflow bindings for revalidation. Revalidate against current approved ontology and technical tool permissions. Retain historical versions and failure traces.

Replay is an explicit durable decision with eligibility, reason and originating run/correction IDs. Use existing run submission and approval controls, with an idempotency key tying replay to the correction. Read-only runs can be eligible; completed writes need duplicate-effect reconciliation and unknown outcomes stay blocked. Do not grant tools or change shared workflow schemas through ontology metadata. Any necessary canonical contract extension goes through the existing joint-review gate.

## Risks / Trade-offs

- Sparse SME labels → expose uncalibrated states; obtain real reviewed Simpsons examples before automatic acceptance.
- Sampling misses rare anomalies → report coverage and denominators; never promote sample observations into population facts.
- Permission changes leak historical evidence → reauthorize all lookups, exports, traversal and cached context.
- Large dependency closures → bounded indexed traversal with explicit incomplete responses and no silent constraint omission.
- Semantic corrections cause repeated writes → separate impact/revalidation from replay and require existing authorization and reconciliation.
- Legacy inferred-context consumers → explicit migration tests proving approved-only business context while retaining technical join behavior.

## Migration Plan

1. Add idempotent scoped tables/indexes and validation schemas; test SQLite and configured PostgreSQL compatibility on isolated stores.
2. Backfill source lineage and legacy candidates as drafts without changing stored credentials or published workflows.
3. Enable profile collection, layered authoring and review through existing Data Intelligence.
4. Validate calibration machinery; retain production automatic acceptance disabled until evidence gates pass.
5. Publish the first reviewed ontology, migrate retrieval to version manifests and register workflow/run dependencies.
6. Run offline lifecycle tests, contracts, frontend checks and isolated drift/replay scenarios. Perform bounded read-only Simpsons acceptance and record unresolved definitions honestly.
7. Load validated code through the project's established deployment process. Roll back routing/feature activation while preserving immutable audit/history; use backward-compatible additive migrations rather than deleting new evidence.

## Simpsons descriptive draft construction

The supplied review is explicitly documented current application behaviour, not business-confirmed policy. Build a curated, unpublished instance in a new isolated local database using only existing saved metadata/profiles. Preserve exact review hashes and per-assertion provenance, distinguish declared ID references from unverified text associations, and keep unsupported policy details unresolved. Do not mark the draft approved merely to demonstrate a question. Extract and reuse the existing pure ontology dependency closure for draft previews while retaining authenticated approved-version checks on production selection. The three previews are graph/context coverage demonstrations only, with no record query, workflow plan or execution.


## Business graph presentation

Owner feedback requires the ontology to open as a business concept graph with labelled relationships rather than a record-management screen. Reuse the existing canvas/library stack against the approved foundation API, without replacing it with the legacy semantic graph. Show clear concept meanings, mapped field/source names, constraints, review state and evidence limits in readable inspectors. Keep seven unresolved fields visible as pending verification, with no invented values or confidence. Preserve advanced review/publication controls behind an explicit management mode; raw JSON is optional diagnostic/export content. This is frontend presentation only and does not load source record instances or alter ontology authority. Verify the actual rendered diagram on desktop and mobile before a frontend-only release.

## Authorized object-access extension — 31 October 2026

Implement docs/ontology-review/simpsons/architecture-design.md following explicit owner authorization. Extend the existing QueryReader with a bounded projected read primitive supporting native Mongo ObjectId and PostgreSQL primary keys; an ontology adapter resolves approved concepts/fields and references into these reads. This is not a second planning/query engine. Do not depend on model generation or legacy semantic approval to browse an approved concept. Keep technical join grants separate: expansion performs independently authorized one-hop reads and describes observed references or candidates, never issues join/execution permission.

Add POST /ontology/v1/objects for list/search/detail and POST /ontology/v1/objects/expand for one-hop expansion. Read-only POSTs retain current session/origin guards. Resolve collection/field identifiers exclusively from approved current mappings. Only approved bound scalar attributes and verified native identity columns may be projected; exclude credential/secret fields server-side. Use current connection-owner scope plus tools.read and workspace:read. Return explicit continuation/freshness and per-field missing states, never bulk source persistence. Sign cursor bindings to scope, version, metadata generation, filters and field projection; bound pagination. Reject stale versions and changed authority before returning data. Multiple serial candidates remain distinct source identities; physical engine resolution remains unavailable. The UI opens definitions on box selection and offers explicit record browsing, object selection and related-record navigation. No automatic workflow submission, new context/recovery engine, source writes or fabricated values.
