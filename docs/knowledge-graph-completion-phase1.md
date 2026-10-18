# Knowledge graph completion — remaining-scope Phase 1

This phase extends the existing Atlas/Supabase metadata graph. It is separate from
the historical query-pushdown/federation/job phases. It adds no database CRUD,
workflow database nodes, EDA, cloud business reads or model calls.

## UI

Open **Data Intelligence → Relationships → Detailed knowledge graph**.

- **Technical structure:** expand connection → database → PostgreSQL schema →
  table/view → fields, or Atlas connection → database → collection → fields.
  Search finds nodes without first expanding branches. Connection filters and
  parent navigation narrow exploration. The detail panel exposes snapshot types,
  nullability/defaults when discovered, indexes, constraints and Mongo validation.
- **Business entities:** review dataset/identifier naming suggestions and their
  source-qualified mappings. Select a mapping, correct its entity name/role, and
  Confirm, Reject or Reset. Datasets represent entities; fields identify,
  reference or describe them. Select Inspect entity to navigate its linked
  source mappings. Confirmation supplies business meaning, not execution grants.
- **Relationship evidence:** inspect linking fields, metadata evidence strength,
  declared direction, qualified uniqueness and unknown overlap/cardinality. Review
  suggestions directly or use the existing Relationship map. Declared database
  constraints cannot be reclassified by a review button.

The existing map, dataset/field descriptions, graph review and Questions remain
available. Reads use the existing server-owned workspace/subject authority;
management requires tools.assign in addition to read access. Read-only and stale
views disable edits. This does not add individual production login to the shared
demo deployment.

## Inference and honest limits

Business concepts use conservative dataset-name singularization and specific
identifier stems, with manual correction. There is no hardcoded Northwind
ontology, LLM-generated meaning, statistical confidence percentage or claim that
names prove business semantics. English suffix heuristics can suggest awkward or
incorrect names: review them. A rejected or needs-review mapping is not confirmed.

Foreign keys retain the exact declared field order and source-to-target direction.
Named scalar identifiers can suggest links between Mongo collections as well as
across sources. Collection-qualified identifiers may suggest a reference to a
target _id. Generic id-to-id pairs, nested/array identifiers and mixed types do
not generate arbitrary links. Matching ObjectId references are metadata-only
suggestions; the existing read engine's key-type restrictions remain in force.

Qualifiers distinguish a declared relationship from a metadata candidate. A
matching complete primary/unique constraint supplies metadata uniqueness evidence;
a composite constraint does not establish uniqueness for just one member field.
Reported Mongo unique indexes do not establish global uniqueness when sparse,
partial or collation applicability is unknown. Acceptance does not prove value
overlap, source coverage, non-null keys or actual cardinality. Existing query
validation and execution-time strict join checks still apply.

The v2 projection caps its output at 16,000 nodes and 8 MB, failing explicitly
instead of returning an apparently complete truncated graph. Existing inference
node/relationship/candidate limits remain, including the 20,000 comparison bound.
The technical tree/search and business lists page in batches of 100; the existing
map remains limited to 24 datasets. Focused relationship details show the first
100 with a narrowing notice. Entity details and the searchable Business entities
list expose their complete mapping sets in batches of 100.
Underlying snapshot discovery remains bounded/sampled, so missing Mongo fields
are not proof of deletion.

## Phase 2 source navigation follow-up

This document's "remaining-scope Phase 1" completes the knowledge graph portion
of the original six-phase plan's **Phase 2: Detailed metadata catalog and
knowledge graph**. It is not the separate query pushdown/federation/job numbering.

Entity details now show visible/total mapping counts and load further sources in
100-item pages. Every linked source is inspectable directly from its entity,
including mappings beyond the first 100. The page remains expanded when the same
entity refreshes; navigating away and back starts with the first page.

Relationship field pairs are clickable and labelled with their complete
connection/database/schema/dataset/field path (MongoDB omits schema). Selecting
either endpoint opens that exact field's metadata and mapping review. Declared
relationships retain their arrow direction; inferred links retain unknown
direction. Navigation works with read-only permissions and historical graphs;
review controls remain disabled in both cases. These changes add no backend
routes, inference, execution grants or source-data reads/writes.

Manual acceptance:

1. Open Relationships → Detailed knowledge graph. Expand relationship evidence
   and select each linking field; check its stable ID, full path and metadata.
2. Open Business entities → a mapping → Inspect entity. Check source counts and
   follow a source link. With more than 100 mappings, use Show more entity sources
   and inspect an item beyond the first page.
3. Repeat with read-only access and a historical fixture: navigation must work,
   while mutation controls remain disabled.

Fresh verification and deployment status for this follow-up are recorded in
`openspec/changes/knowledge-graph-phase2-navigation/verification.md`. Earlier
deployment evidence below describes the earlier release.

## API and compatibility

- `GET /data-relationships/v2`: explicit version 2, original graph revision,
  database/schema/entity nodes, snapshot metadata, business mappings and qualified
  relationship evidence.
- `POST /data-relationships/v2/mapping/{node_id}`: exact body
  `{revision, entity_name, role, status}`. Name is limited to 80 characters;
  role is represents/identifier/reference/attribute, with dataset/field checks;
  status is suggested/confirmed/rejected. Suggested resets the saved review.
- Existing `/data-relationships`, build, annotation and relationship-review routes
  retain their v1 shape and authority. No workflow/agent/tool contract changed.
  The additive graph contract is `shared/contracts/data-sources/relationships-v2.schema.json`.

`workflow_api/data_graph_v2.py` projects the graph from its matching persisted
snapshots, including when a newer profile makes the current graph historical.
Projection never decrypts source credentials or opens a cloud connection.
Stable connection/dataset/field IDs are unchanged; database/schema IDs derive from
their actual parent/namespace, and entity IDs derive from normalized names.

Owned entity reviews and minimal audit events use additive tables
`data_graph_entity_reviews` and `data_graph_audit`. Structural fingerprints exclude
sample-presence/sample-size counts. Unchanged evidence retains reviews; changed
evidence becomes needs_review. Explicit reset removes the manual mapping review.
Disconnected source nodes/mappings are hidden immediately. Mapping edits check the
current revision in the same transaction, increment it and invalidate old query
plans. Entity confirmation never accepts or inserts an executable relationship.

No original Praxi source files or runtime dependencies are used or modified.

## Acceptance sequence

1. Open the detailed graph and expand both connection hierarchies. Compare the
   database/schema/dataset/field structure with existing discovered metadata.
2. Select a field and inspect metadata. Inspect a declared foreign key and a
   suggestion; verify ordered field pairs and explicit unknown facts.
3. On an isolated test graph, select Business entities → a mapping. Confirm,
   reload, reject, reset and correct its entity/role. Inspect its shared entity.
4. Repeat without management permission and with a stale graph: edits must fail.
5. Refresh unchanged fixtures/rebuild: IDs/reviews remain stable. Change relevant
   structural evidence/rebuild: the mapping needs review. Sample-count changes
   alone do not invalidate it. Disconnect a fixture and verify it disappears.
6. Create a read plan, edit an entity mapping and attempt the old plan: reject it
   as stale before business reads. Replan normally to continue.
7. Repeat on desktop/mobile; check expandable navigation, search, filters,
   dialogs/fields and document-width overflow. Real iPhone testing is separate
   from browser-engine/emulated-mobile testing.

Verified and deployed on 18 October 2026 (IST): 194 backend regressions, 41
Google/procurement regressions, 121 frontend/domain/proxy tests and 16
desktop/mobile fixture browser scenarios passed, alongside types, scoped lint,
production build, contracts and strict OpenSpec. Live desktop/mobile Chromium
and mobile WebKit verified actual metadata navigation and reload without edits,
page errors, chunk 404s or horizontal overflow. Physical iOS testing remains a
separate user check. Existing IDs/reviews were preserved; 33 new business mappings
remain suggested for explicit user review. See
`openspec/changes/knowledge-graph-completion-phase1/verification.md` for evidence.
Browser fixtures are not evidence of live review decisions or live cloud writes.

## Build feedback correction — 18 October 2026

The detailed explorer now reads immediately after a build request, polls queued or
running builds every second, and shares its accepted status with the parent build
button. Idle reads remain six seconds apart. Rebuilding preserves the current
selection and explorer mode; superseded responses cannot restore an older status.
The relationship map retains its existing polling and v1 graph shape.

Verification: 124 frontend/domain/proxy regressions, three focused race/build
scenarios (included in 124), 16 production desktop/mobile browser scenarios,
types, scoped lint, production build and contract/drift checks passed. A live
metadata-only worker build measured 0.741 seconds before the UI correction. After
deployment, build-to-visible-revision/button-ready measured 3.462 seconds desktop
Chromium, 2.466 seconds mobile Chromium and 2.519 seconds mobile WebKit. These are
observations, not latency guarantees or physical iPhone measurements. No page
errors, missing static assets or lost selections occurred in those live checks.
Only the frontend was restarted; backend inference, permissions and source data
were unchanged. Previous static assets were retained for older open tabs.
