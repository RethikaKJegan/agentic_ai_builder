# Tasks

Scope: user Section 1, subsections 1.1–1.6 only. Numbered groups below are implementation batches, not authorization for later product sections. Existing retrieval, planning and execution remain authoritative. Ontology selection includes concepts and dependencies only; impact/replay integration adds eligibility and existing authorised submission hooks, never a context or recovery engine. Ordinary business graph cycles are valid; only explicit acyclic predicates and merge redirects prohibit cycles.

## 1. Durable ontology records and compatibility

- [x] 1.1 Add validated schemas and additive scoped persistence for concepts, typed attributes, mappings, constraints, evidence, assessments, versions and dependencies; verify schema rejection cases, tenant isolation and migration idempotency on SQLite and the configured PostgreSQL adapter.
- [x] 1.2 Import existing source mappings, semantic proposals and reviews as provenance-preserving drafts; verify existing connections/reviews remain unchanged and no imported suggestion becomes automatically approved; document migration and rollback.

## 2. Catalogue, source capabilities and profiling

- [x] 2.1 Extend connector capability responses and catalogue records with ownership, source descriptions, lineage, effective permissions and unavailable metadata states; verify Atlas/Supabase and applicable existing application connector fixtures and document actual coverage.
- [x] 2.2 Add bounded value-profile jobs for null rates, uniqueness, distributions and anomaly observations with revisions, sample basis and freshness; verify null/missing distinctions, mixed types, empty datasets, permissions, job fences and resource limits; document profiling semantics.
- [x] 2.3 Add type-safe candidate overlap and referential-consistency evidence including composite keys; verify known matches, contradictions, incompatible types and incomplete samples without persisting bulk source values.
- [x] 2.4 Add checkpoint/pagination/rate-limit support where connectors expose it, declaring bounded-discovery fallbacks elsewhere; verify retries, continuation, failure recovery and obsolete-result rejection with adapter tests and capability documentation.
- [x] 2.5 Implement changed-component metadata/profile comparison and dependency invalidation for source additions, schema/key changes and verified rename continuity; verify unchanged approvals survive, ambiguous renames require review and sampled omissions do not prove deletion.

## 3. Layered business graph and definitions

- [x] 3.1 Implement stable-ID common/domain/organization graph records, typed attributes, source mappings and dependency links; verify cross-layer composition, rename identity and source lineage without name-based identity collisions.
- [x] 3.2 Add documented reusable definitions for Sales, Procurement, Finance and Customer Service plus organization terminology, custom fields, approval hierarchies and supported business constraints; verify provenance and that template availability does not assert Simpsons mappings as facts.
- [x] 3.3 Separate observed facts, model inferences, statistical findings and hypotheses in candidate generation/storage and graph responses; verify FK structure does not approve business semantics and correlation alone never approves relationships; document evidence classes.
- [x] 3.4 Add graph/type/rule validation and merge redirects with rule-specific cycle/conflict detection; verify dangling endpoints, incompatible mappings, historical IDs and conflicting constraints are handled explicitly.

## 4. Scoring, review and evaluation

- [x] 4.1 Implement versioned per-signal assessments for schema/types, keys/values, semantic similarity, overlap/profiles, constraints, freshness and contradictions; verify missing evidence and conflicting signals remain visible and document score interpretation.
- [x] 4.2 Retain immutable original proposals and expert correction labels; implement held-out evaluation and calibration artifacts with sample counts, precision uncertainty and risk policy gates; verify absent/insufficient labels cannot enable automatic acceptance and synthetic labels do not establish production calibration.
- [x] 4.3 Implement optimistic-concurrency review APIs for accept/reject/correct/merge with reviewer identity, reasons and downstream impacts; verify stale writes, permissions, audit retention and merge compatibility.
- [x] 4.4 Extend Data Intelligence review UI with layer-aware concepts, constraints, evidence, score availability, conflicts, dependencies and prioritized queue; verify reviewer/viewer behavior, accessible desktop/mobile review flows and frontend API schemas; document review operations.
- [x] 4.5 Expose unresolved mappings, precision, false positives, corrections, drift and downstream failure metrics with denominators/version filters; verify empty denominators render unavailable and labelled outcomes produce expected metrics.

## 5. Publication, controlled access and task resolution

- [x] 5.1 Implement atomic idempotent approved publication and immutable version manifests pinning evidence, validation and calibration; verify blocking conflicts, concurrent publication, stale source evidence and rollback preservation; document draft/publication boundaries.
- [x] 5.2 Add authenticated ontology-v1 APIs for concept/source-field/entity/type lookup, version history and bounded export; verify current permission enforcement across historical reads and derived evidence, no cross-tenant leakage and stable error contracts.
- [x] 5.3 Implement bounded task dependency closure across layers with version-pinned context manifests; verify required constraints/dependencies are retained, unrelated concepts excluded and overflow/missing context explicit.
- [x] 5.4 Integrate approved ontology manifests into existing source retrieval/planning while preserving separate technical join authorization; verify unreviewed semantics are excluded from authoritative task context, revoked access invalidates cache use and existing workflow/tool contracts still validate.
- [x] 5.5 Add UI publication/version/history/export controls and task-context inspection; verify stale publication feedback, evidence visibility and meaningful desktop/mobile browser flows; document API examples and operator workflow.

## 6. Corrections, dependency impact and workflow lineage

- [x] 6.1 Register actual ontology manifests at workflow planning and run consumption, linking source evidence through relationship/version/context to run; verify a failed fixture run can be traced to its exact consumed definition without changing execution authority.
- [x] 6.2 Implement correction-triggered affected-cache invalidation and workflow/relationship revalidation; verify unrelated dependencies remain valid, historical manifests survive and changed interpretations cannot silently continue.
- [x] 6.3 Implement durable replay eligibility/decision records and integration through existing authorized run submission; verify idempotency, approval requirements, safe read replay, completed-write reconciliation and blocked unknown external outcomes; document operator recovery.

## 7. End-to-end verification and Simpsons acceptance

- [x] 7.1 Run integrated catalogue-to-publication-to-task-context-to-correction scenarios with isolated PostgreSQL/Mongo source fixtures, including schema drift and replay failure cases; retain evidence tied to each specification scenario.
- [x] 7.2 Verify the existing Simpsons connection identity/scope and perform bounded read-only catalogue/profile/layered-mapping acceptance; record real SME review requirements, calibration coverage and unresolved business definitions without fabricating approvals or changing source schemas.
- [ ] 7.3 Demonstrate reviewed Simpsons publication, permission-scoped task retrieval and correction lineage once required expert definitions are available; retain original output/corrections and report incomplete gates explicitly until satisfied.
- [x] 7.4 Run relevant backend regressions, frontend types/lint/build/tests and desktop/mobile flows, shared contract validation/drift checks, strict OpenSpec validation and diff checks; deliver a requirement-by-requirement verification report distinguishing local implementation from loaded/deployed behavior.

## 8. Simpsons descriptive draft from supplied application review

- [x] 8.1 Build a reproducible layered Simpsons draft and bind documented assertions to saved collection/field evidence; retain review hashes, unknown mappings and unsupported policy details; verify native record/graph validation without company I/O or approvals.
- [x] 8.2 Load the draft into a separate local database with copied metadata/profiles and no credentials; reuse ontology dependency selection for three explicitly unpublished previews; verify approved APIs still reject draft use and the saved input is unchanged and the live application database is never opened.
- [x] 8.3 Export readable and machine-readable draft/preview artifacts, run relevant construction and ontology regressions, and update verification without marking actual policy approval/publication complete.

## 9. Technical follow-up without business approval

- [x] 9.1 Verify the eleven unresolved field bindings through bounded read-only collection/schema and field-type probes using the existing Simpsons connector; retain per-field outcomes and access/time limits, distinguish empty collections and unobserved fields from schema absence, and preserve the draft/publication boundary.

- [x] 9.2 Add the technically observed fields and hashed probe provenance to a new isolated unpublished draft, retaining the original draft and unconfirmed reference/business semantics; verify bounded previews, native validation and relevant regressions.

## 10. Owner-approved publication and UI deployment

- [x] 10.1 Record the owner approval and publish the technically supported Simpsons definitions through existing ontology review/version controls; keep seven unresolved bindings as drafts, preserve source credentials/legacy reviews/workflows and retain an application rollback backup.
- [x] 10.2 Build and verify the frontend in isolation, deploy through existing services with rollback, and verify authenticated desktop/mobile ontology review, evidence, published version and bounded concept selection against the loaded application.

- [x] 10.3 Preserve explicitly targeted field observations across later sampled omissions, retain current observed type contradictions and declared-schema authority, and verify a resumed live worker does not stale an unchanged approved Simpsons definition.

## 11. Business graph presentation correction

- [x] 11.1 Make a connected labelled concept graph the default ontology view, with overview/all-concept and layer/search controls, readable concept/relationship/field/rule/source inspection, honest pending states and optional advanced management; preserve ontology records, approvals, APIs and source data.
- [x] 11.2 Verify graph/evidence projection, management compatibility, readable desktop/mobile graph interaction and empty states; build and deploy the frontend only with rollback and read-only live checks showing unchanged backend ontology/source/workflow state.

## Workflow follow-up

## 12. Owner-authorized business object explorer

Scope extension authorized on 31 October 2026: implement the architecture-design.md record explorer and deploy after verification. Preserve definition-only task selection and existing execution/recovery services.

- [x] 12.1 Add version-pinned, owner-scoped object list/detail/reference-expansion APIs over the existing connector read boundary, with native stable keys, server-side safe field projections, bounded continuation, honest missing/ambiguous states and no source writes; verify permissions, stale definitions, type safety, limits and candidate/reference distinctions.
- [x] 12.2 Add concept-box browsing, source-backed object details and labelled relationship exploration to the existing ontology UI; retain readable definitions, task selection and review controls, support desktop/mobile and reject stale async results.
- [x] 12.3 Verify API/UI contracts, backend regressions, types/lint/build and desktop/mobile flows, then deploy with rollback and bounded read-only live Simpsons checks; document loaded behavior and remaining business gates.

- Archive only after complete implementation evidence and applicable project review requirements are satisfied.
