# Ontology foundation — Section 1.1–1.6

**31 October update:** the [source-backed Simpsons record explorer](ontology-review/simpsons/object-explorer.md) adds native record browsing and one-hop relationship inspection to the business concept graph. Existing definition-only task selection and execution/recovery authority remain unchanged.

This implementation extends the existing authenticated source/graph services. It adds ontology construction, review and approved publication. Existing `/data-sources`, `/data-relationships`, `/data-ontology`, `/knowledge-graph`, workflow and run APIs keep their response shapes. No new context, planning, execution or recovery engine is introduced.

## Source catalogue and profiling (1.1)

Open **Data Intelligence → Ontology**. Import source suggestions, then request a bounded record sample for a connected source when needed. Profiling uses the existing durable profile jobs, leases, credential generation checks and worker. Refresh ontology after the job finishes; import suggestions again to construct new candidates.

Supported database adapters remain MongoDB Atlas and Supabase PostgreSQL. Their metadata cursors handle bounded discovery; scheduled snapshot comparison is advertised as such, not as CDC or incremental record synchronization. Existing application integrations are unchanged; unsupported synchronization/checkpoint/grant-enumeration capabilities are explicitly unavailable. This change does not add arbitrary enterprise connector implementations.

MongoDB reads at most 25 documents per collection using existing discovery limits. PostgreSQL reads at most 100 rows per table with a 2-second sample query deadline inside the existing 60-second source profile budget. Source metadata stays in its original schema; ontology profile summaries use separate storage. Profiles are subject to source credentials, RLS and existing configured source scope. Failed samples report unavailable coverage. Source ownership/grant enumeration that the connector cannot establish is labelled unavailable; application connection ownership is known.

Profiles include actual denominators for missing fields, explicit nulls, scalar uniqueness, hashed value frequencies, bounded typed key overlap, composite-key profiles and IQR anomaly counts. Nested values are distinguished from missing fields. Unsupported nested/array comparisons remain unavailable. Sample coverage is never population referential integrity. Raw sampled records are not stored in the ontology; value hashes are scoped evidence accessible to the source owner, not anonymization guarantees.

Existing snapshot changes identify additions/removals/key changes. Potential field renames are naming/type hypotheses and never transfer approvals automatically. An expert can correct an existing stable ontology record to the verified current source reference. Mongo sample omissions are not proof of deletion. Unchanged source components retain their signature; affected definitions and transitive consumers require revalidation.

## Layered business graph (1.2–1.3)

Records have stable IDs, layer, kind, definition, explicit dependencies, source references, source signatures/revision lineage, evidence class, assessment and revision. Kinds are `concept`, `attribute`, `mapping`, `constraint` and `relationship`. Layers are `common`, `domain` and `organization`.

Starter definitions cover Party, Sales Customer, Procurement Supplier, Finance Invoice and Customer Service Case. They are editable drafts with documented starter provenance, not asserted Simpsons definitions. Organization terms and custom fields map to shared definitions through explicit mappings. Approval hierarchies are typed relationships, optionally with an explicit acyclic rule and required approval-role constraints.

Source dataset/field records and structural relationships import as drafts. Legacy entity mappings, semantic proposals and reviewed interpretations retain their evidence in import history without automatic approval. Definition similarity proposes mappings; bounded typed sample overlap proposes statistical observations. Neither proves business meaning. Source FK evidence proves a structural link separately from any business predicate.

Evidence classes are `observed_fact`, `model_inference`, `statistical_finding` and `unverified_hypothesis`. A reviewed inference can be approved while retaining the fact that its original method was inference.

Supported constraints include required attributes, allowed values, numeric ranges and approval roles. Graph validation checks endpoints, dependency closure, attribute compatibility and conflicting mapped types. Ordinary graph cycles are valid. Only predicates explicitly marked acyclic and merge redirect chains reject cycles. Unsupported business-rule forms fail validation rather than becoming executable rules.

## Assessment and review (1.4–1.5)

The inspector exposes source evidence, assessment availability, contradictions, direct dependent records and actual workflow/run consumers. Review prioritizes uncertainty/staleness, risk and dependency impact. Search and layer filters make larger imported catalogues navigable.

Assessments use compatible types, declared key evidence, definition/name similarity, available typed value/composite-key overlap, source freshness and contradictions. Freshness uses a documented 24-hour heuristic window. The aggregate is a heuristic rank, never a probability. Typed graph constraints are a separate publication/approval gate.

Calibration uses retained accept/reject/correct labels, groups related fields by source dataset family, and holds out deterministic independent groups. An empirical five-bin calibration artifact records sample counts, precision, false-positive rate, Wilson precision lower bound and label digest. Automatic acceptance requires adequate applicable calibration for the same record kind/domain, adequate bin support, a precision lower bound meeting policy, explicit low mapping risk, no contradictions and no downstream consumers. Synthetic tests verify calculation only; they do not supply production calibration evidence.

All review/edit actions use expected revisions. Corrections preserve the immutable original suggestion and expert decision/reason. Approved source or dependency evidence that changes becomes stale. Correct the record with current references and revalidate before publication. Merges preserve the old ID as an explicit redirect; dependent mappings must be corrected first. Incompatible merges are rejected.

Publication takes the current draft revision and publishes approved records only, checking complete approved dependencies, typed consistency and current evidence atomically. Identical content publication is idempotent. Published versions retain evidence, source lineage, calibration artifacts and validation results. Drafts remain editable separately.

## Controlled access and ontology selection (1.6)

All routes use existing session, origin, `tools.read` and `tools.assign` gates and workspace/owner scoping. Historical versions and correction history enforce current source access. A removed field in an otherwise authorized source retains historical lineage and is stale for current use; a disconnected/deleted/no-longer-owned connection is unavailable.

- `GET /ontology/v1` — draft view, catalogue, review queue, version summaries, impacts and metrics.
- `GET /ontology/v1/metrics?version_id=...&calibration_id=...` — version-filtered records and the selected held-out evaluation artifact.
- `POST /ontology/v1/sync` with `{}` — import source/legacy suggestions and construct bounded candidates.
- `POST /ontology/v1/templates` with `{}` — add starter definitions as drafts.
- `POST /ontology/v1/profile/{connection_id}` — queue an opt-in bounded sample through the existing worker (202).
- `POST /ontology/v1/record` — `{record, expected_revision}`; use 0 for a new stable ID.
- `POST /ontology/v1/review/{id}` — `{expected_revision, action, reason}`; correct adds `record`, merge adds `target_id`.
- `GET /ontology/v1/history/{id}` — original suggestions and reviewed changes.
- `POST /ontology/v1/calibrate` — `{minimum_precision, minimum_examples, kind?, domain?}`; minimum 20 examples, default kind mapping.
- `POST /ontology/v1/assess` — `{record_id, expected_revision, calibration_id, auto_accept}`; unmet gates reject the request.
- `POST /ontology/v1/publish` — `{revision}`.
- `GET /ontology/v1/versions/{version_id}` and `/export` — approved version with evidence.
- `GET /ontology/v1/versions/{version_id}/lookup?kind=concept|source_field|entity|relationship_type&value=...` — controlled lookup.
- `POST /ontology/v1/select` — `{version_id, concept_ids}`; selects concepts plus required ontology dependencies, with a maximum of 200 records and explicit overflow errors.
- `POST /ontology/v1/replay/{impact_id}` — `{action: "assess"}` or `{action: "submit", inputs, idempotency_key, workflow_version?}`.

Example new concept:

```json
{"record":{"id":"organization:customer","kind":"concept","layer":"organization","label":"Customer","definition":"A buying party; supply the organization's reviewed definition.","dependencies":[],"source_refs":[],"evidence_class":"unverified_hypothesis","properties":{}},"expected_revision":0}
```

`select` is ontology graph selection only. It returns version-pinned IDs, revisions, evidence and selected definitions. Existing planning can receive `context.ontology_concepts = {version_id, concept_ids}`. The server resolves it, attaches the owned selection ID, and validates it on workflow saving. Existing runtime revision validation checks it before submission and subsequent execution checks; run creation records actual consumption in the same transaction.

Verified corrections invalidate affected selections and record workflow/run impact. Revalidation requires a current approved selection and the existing reviewed workflow revision flow. The impact API assesses eligibility and submits only through the existing authorized `execute_workflow` service. Write-capable/unclassified workflows require reconciliation; it does not replay their external effects. An explicit `workflow_version` can identify a replacement revision of the same workflow after it has passed the existing review/approval flow; the original affected run remains linked in the impact record. Existing scopes, approvals, retry keys and execution checks remain authoritative. Submission results and unknown outcomes are audited. No recovery executor is added.

## Migration and rollback

Creation is additive/idempotent for SQLite and the existing PostgreSQL adapter. New `ontology_*` tables contain records, events, profiles/requests, versions, selections, impacts and calibration artifacts. Existing source credentials, snapshots, legacy reviews, workflow schemas and executable tool contracts are unchanged. Load the code through the existing application deployment process. For rollback, restore prior routing/code while retaining additive tables and immutable audit data. Do not erase source history or infer approval of legacy imports.

See the change's `verification.md` for actual checks and outstanding business-validation gates.


## Loaded Simpsons release

The [owner-approved Simpsons release](ontology-review/simpsons/deployment.md) is deployed. Open Data Intelligence → Ontology to review 409 approved records and seven unresolved drafts. Calibration remains unavailable. Targeted field observations are retained separately from sampled metadata and scoped to the same connection/credential fingerprint; later sampled omissions alone cannot revoke those observations. Explicit schema prohibitions, changed observed types and current access checks remain authoritative.


## Business graph view

Data Intelligence → Ontology now opens the [connected business graph](ontology-review/simpsons/graph-ui.md). Concept and connection clicks show readable meanings, fields, rules and source evidence. Review & manage retains the advanced authoring/publication workflows; technical JSON is not the default user-facing ontology.
