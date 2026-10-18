# Knowledge graph and automatic metadata refresh — Phase 1

This is Phase 1 of the two-phase KG improvement plan. It extends the existing
Atlas/Supabase graph. Phase 2 pre-planning retrieval, instance-level customer/order
records, arbitrary new executable joins, database CRUD changes and Google actions
are outside this change. Praxi is not modified or imported.

## UI acceptance

1. Reload the app after deployment. Open Data Intelligence → Relationships →
   Knowledge graph. The existing Relationship map and Detailed knowledge graph
   remain available.
2. Inspect the entity network. Nodes are business concepts inferred from existing
   dataset/identifier mappings. Edges come from existing technical relationships.
   Initial predicates are conservative: `references` for declared foreign keys and
   `is related to` for suggestions. Product/Supplier/Category labels are not seeded
   or hardcoded. Use Detailed knowledge graph to correct underlying entity mappings.
3. Select an entity. Expand its source mappings to inspect the actual qualified
   source paths, field types and available metadata/constraints. The canvas contains
   no individual customers, employees or order records.
4. Select a business relationship. Inspect both exact technical field paths and
   Relationship evidence and limitations. A declared FK and an accepted metadata
   suggestion remain distinct. Business arrow direction is interpretation, not
   proof of cardinality or permission to execute a join.
5. For a test relationship, enter a meaningful label and adjust Reverse business
   direction if appropriate. Example: Product → references → Supplier can become
   Supplier → supplies → Product. Click Confirm relationship. Reload and verify
   the label and direction persist. Reject business relationship fades the edge;
   Reset business review restores the default suggestion. These actions edit only
   application metadata. Technical relationship acceptance is unchanged.
6. Zoom, Fit ontology, drag to pan, search and filter by connection. The canvas
   displays at most 80 matching entities; search/filter accesses the remainder.
   The selected inspector retains its focus across ordinary polling. Dense parallel
   relationships may require zoom and focused exploration.
7. Automatic metadata refresh is available here and under Connections. Choose a
   connection, set an interval (60–86400 seconds), and Save refresh settings.
   The default is enabled every 300 seconds; existing saved sources receive a first
   check five minutes after initial scheduler installation. Saving settings schedules
   the next check one interval later; it does not immediately profile.
8. Leave automatic refresh enabled and the backend worker running. In a dedicated
   test database, add a table/collection or field inside the configured database/
   schemas. MongoDB collections need representative documents to discover fields.
   Do not click manual Refresh metadata. After the interval plus bounded profile/
   build time, confirm the metadata revision and graph update. Inspect Last attempted,
   Last successful, Last discovered change and Next check. Browser polling updates
   the display; the worker performs discovery even with the page closed.
9. Repeat without structural changes. An unchanged automatic check updates freshness
   without advancing metadata/graph revisions. Sample counts alone are ignored for
   this comparison. Relevant schema/type/index/constraint or coverage changes create
   a new snapshot and queue a graph rebuild. Existing explicit manual refresh retains
   its previous revision/invalidation behavior.
10. Confirm a test predicate, then change supporting structural evidence or its
    business mapping. After refresh/rebuild, expect needs_review. Historical graphs
    disable reviews. Unchanged evidence preserves reviews across rebuilds.
11. Disable automatic refresh and verify future scheduled checks stop. An already
    claimed check may finish. Disconnecting a dedicated test connection cancels its
    profiles and removes dependent source mappings/edges from current visibility.
12. Test failure/recovery only with an isolated connection. Failure retains the last
    successful snapshot and exposes safe error text. Automatic retries use exponential
    backoff up to 24 hours. Resuming after new credentials uses normal connection setup.
13. Repeat navigation, review, reload, search and zoom at desktop and mobile widths.

A newly added database must first be connected through the existing authorized
connection flow. Automatic discovery stays inside configured databases/schemas;
it does not scan all databases on a server or expand credential authority. MongoDB
profiling samples bounded documents; values are not saved as ontology facts.
Sample omissions do not establish field deletion. Existing discovery/node bounds
still apply. This is scheduled refresh, not instantaneous change-stream delivery.

## API and persistence

All routes use existing authenticated workspace/subject ownership, origin checks,
safe error envelopes and Cache-Control: no-store. Reads require tools.read;
management additionally requires tools.assign through the existing identity gate.

- GET /data-ontology: ontology-v1 projection with entity sources, predicates,
  source field pairs, technical review status and evidence.
- POST /data-ontology/{relationship_id}: exact revision, predicate, reversed and
  status (suggested/confirmed/rejected). Stale writes return 409.
- GET /data-refresh: refresh-v1 owned connection status and schedule.
- POST /data-refresh/{connection_id}: enabled and interval_seconds.

New tables: data_ontology_reviews, data_ontology_audit, data_source_refresh and
  data_source_auto_jobs. All creation is additive/idempotent. Existing connection
  and graph response contracts remain unchanged. Ontology review revisions are
  independent of technical query-grant revisions. No contributor signoff is inferred.

The worker schedules at most one due automatic job per tick, coalesces active work,
uses the existing durable lease/token/generation checks, and performs network I/O
outside application transactions. Unknown outcomes do not publish obsolete metadata.
Automatic refresh never registers database write permissions. Existing shared-demo
identity and source/query limits remain; this does not implement production multiuser IAM.

Verification and deployment evidence are recorded in
openspec/changes/business-ontology-phase1/verification.md.
