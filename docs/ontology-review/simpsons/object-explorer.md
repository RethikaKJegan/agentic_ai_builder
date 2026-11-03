# Simpsons source-backed record explorer — 31 October 2026

The implementation extends the existing ontology graph with permission-scoped, read-only company record browsing. It is deployed at [Data Intelligence → Ontology](https://praxi.bellcorpstudio.com/app/data-intelligence). The design reference is [architecture-design.md](architecture-design.md).

## User flow

Open Data Intelligence → Ontology. Click a concept box to see its business meaning, fields, rules and sources; the page brings the inspector into view. Choose **Browse … records**, then click a returned record to inspect its actual permitted values. **Explore records** also opens the explorer directly.

The explorer offers exact-field search, bounded pages, native source identity, fetched-at time and a source-evidence panel. Record values distinguish “Not recorded” from “Field not returned”. Approved bound scalar properties are supported; nested objects/arrays and credential fields are excluded. Missing values are not replaced with fictional data. Physical engine is still a logical concept without a verified source identity and cannot be browsed as a resolved physical-engine master.

**Connected records** follows one selected relationship at a time, in either direction where supported. Direct references are described as stored references, rather than independent proof of business ownership. Serial associations are explicitly candidate matches; duplicate invoice candidates retain separate native identities. A null reference, missing target, unavailable binding and failed read remain explicit. A denied subsequent read clears previously displayed values. The definition graph, all-layer navigation, existing review/history/publication/export and definition-only task selection remain available.

Existing workflow navigation, contracts, planner, registry, approvals, runtime and recovery integration remain authoritative. Browsing does not submit a workflow, grant joins, create actions or execute a source write. No per-object executable action is invented.

## Backend boundary

- `POST /ontology/v1/objects`: `{version_id, concept_id, limit?, filter?, key?, cursor?}`. A filter contains at most one permitted field and an exact typed scalar value. Detail uses every native identity field, without filter or continuation.
- `POST /ontology/v1/objects/expand`: `{version_id, concept_id, key, relationship_id}`. Expands one currently approved relationship through independently authorized source reads.

These are read-only POST operations under existing authenticated transport/origin controls. They do not change existing API responses or canonical workflow/agent/tool contracts. The frontend validates the additive response using `frontend/src/api/ontology-objects.ts`; explicit backend shape validation rejects hostile fields, operators and mismatched native values. API payloads remain additive local interfaces; no joint canonical-contract acceptance is inferred.

`workflow_api/ontology_objects.py` resolves approved mappings, source-owner access and current definitions. `QueryReader.objects` adds a bounded projection primitive to the existing query reader/connector boundary: Mongo filters use typed `$eq`, and PostgreSQL identifiers come from the server catalogue with separately bound parameters. Native Mongo ObjectId and PostgreSQL primary-key inputs use existing scalar conversion. There is no model call, alternate query planner or bulk ontology-instance persistence.

Only approved bound scalar fields plus supported native identity columns may be projected. Secret-like field names are excluded before the connector read. Current `tools.read` and `workspace:read` scope and connection ownership are required. The entire selected published version must have current source evidence; corrected current definitions also invalidate their prior published use. Current authority and source-generation binding are rechecked after I/O. A request counter and cancellation prevent the UI from displaying late responses from an earlier selection.

Default pages contain at most 25 records; the maximum is 100. Continuation is encrypted/authenticated, expires after ten minutes and binds scope, ontology version, source revision/generation, permitted fields, filters and page size. Browse depth is limited to 5,000 records with explicit truncation. Relationship expansion returns at most 25 targets and reports truncation with instructions to narrow a direct search. Source timeouts, concurrent-read limits, 64-field projection, 64 KB per projected record and 2 MB result limits apply. Pages are independent live reads, not an immutable snapshot; concurrent source edits can change membership.

## Source-evidence revalidation

The bounded live preflight found metadata drift after the preceding release. The stale-version guard correctly rejected reads. The release retains that guard.

An isolated application-metadata copy was used to verify technical revalidation of 150 existing approved records through the native correction/publication service. The comparison checks unchanged collection identity, keys/indexes/constraints, referenced field IDs/names and non-null types. Sampled null variation and unrelated added fields do not establish new business meanings. The one referenced field with a broader numeric observation, `tickets.hmr`, already has datatype `unknown`; it remains unknown and is excluded from scalar browsing. No unsupported meaning or datatype is approved to make the explorer work.

All 409 previously approved record descriptions/properties/source references are preserved, and seven drafts remain drafts. Technical revalidation retains original proposals/history and existing dependency invalidation; it does not provide independent SME labels or production calibration. Subsequent real drift will continue to require revalidation rather than silently consuming stale definitions.

The owner explicitly approved the live service pause/restart and republication: “Approve live deployment”. Approval evidence and the concrete deployment plan are retained privately under `.local/ontology-foundation/object-release/`.

## Verification evidence

- 117 relevant backend tests passed, covering the new explorer, native identity, duplicate serials, reference traversal, field projection, SQL parameter binding, permissions, in-flight revocation/drift, pagination, input rejection, source limits, no local ontology/source mutation during reads and existing foundation/query/source behavior.
- A final 51-test reader/query follow-up passed after adding native BSON decimal-filter conversion and its regression test. That tested correction was loaded through a separately owner-approved backend restart; it does not change ontology publication or source data.
- 41 workflow/retrieval integration regressions passed; 27 PostgreSQL-backed tests skipped because their independent PostgreSQL fixture was not configured for this run. A focused PostgreSQL projection test verifies quoted identifiers and bound values; live Simpsons acceptance uses MongoDB, not PostgreSQL.
- 18 frontend/proxy tests passed, including record details, explicit candidate navigation, late-response rejection and clearing values after denied access. TypeScript and scoped ESLint passed.
- The isolated production build passed after an ordinary retry. The installed Next.js build emitted its security advisory nudge on the first attempts; no dependencies were upgraded and no advisory remediation is claimed by this release.
- Desktop/mobile browser checks against captured real, permission-filtered Simpsons responses passed: concept click, native record selection, readable source values, account reference, candidate invoice association, company browsing, management compatibility, zero page errors and no horizontal overflow. The two existing management lifecycle browser tests also passed.
- Bounded live connector preflight passed for companies, accounts, tickets and invoices, detail reads, ticket/account and ticket/company references, and candidate ticket/invoice association. Only read queries were issued to Simpsons systems. Actual record responses and screenshots are private; public notes retain coverage without bulk company values.
- Shared contract/schema fixtures, generated UI contract drift, strict OpenSpec validation and diff whitespace checks passed.

Full expert business-policy acceptance and production calibration remain the separate foundation task 7.3. They are not claimed complete by the record explorer.

## Loaded release

Frontend build: `Luy8ChhV-XPO0tJlhuS7D`. Ontology version: `ov_3c9e855088f5ac678e11127661eae182b5189707`. Native source metadata remained at the preflight-tested revisions during activation. The 150 technical corrections and new immutable publication use the existing service, retaining prior versions and original proposals. All 409 business definitions/properties/source bindings are unchanged, and seven unresolved records remain drafts.

Authenticated live desktop/mobile browser checks passed the full concept → source record → account reference → candidate invoice → company navigation flow. Readable underlying values, native IDs, management compatibility, no default raw JSON, no horizontal overflow and zero browser page errors were verified. All non-GET backend requests except the two read-only object endpoints were blocked during browser checks; none were attempted. No workflow was submitted by these checks.

Activation preserved workflow revisions, run records, connector-secret fingerprints, calibration artifacts and targeted source observations while the existing worker was paused. Ontology revisions/history/publication and affected selection/impact state may change through native technical revalidation; this is deliberate dependency bookkeeping. The existing worker resumes afterward, so normal previously authorized scheduled runs may subsequently update runtime history. No Simpsons collection or schema writes were issued.

Rollback retains the previous frontend build, prior backend source, a private 3.9 GB application database backup, activation hashes, approval, preflight and browser evidence under `.local/ontology-foundation/object-release/`. These contain private operational or projected company data and are not public artifacts. The earlier release rollback artifacts remain intact.
