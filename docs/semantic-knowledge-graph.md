# Semantic Knowledge graph

The graph UI is now one **Knowledge graph** tab under Data Intelligence. The
separate Relationship map and Detailed knowledge graph views are removed from
product navigation. Their underlying discovery, annotations, mappings, technical
relationship reviews and query validators remain available as evidence/services.
Legacy API routes remain compatible; the product uses `/knowledge-graph`.

## Entity types and evidence

The entity canvas labels arrows with semantic predicates, independent of status
badges. Unknown meaning appears as **Meaning needs review**, without a directional
semantic arrow. Inferred meaning is dashed and distinct from owner confirmation.
Search matches concepts, source paths and predicates; status filters distinguish
inferred, confirmed, ambiguous, rejected and needs-review edges.

The tab now exposes only regeneration, automatic metadata refresh, connection
selection, search/status filters, an Inspect sidebar and essential zoom/pan/fit controls. Selecting
one connection shows only its source mappings and relationships whose two datasets
belong to that connection. All connections includes cross-database relationships.
These are display filters; they do not restrict the planner's backend KG context.

Select a node to inspect its source metadata, or a relationship to inspect its
meaning, statuses, linking fields, rationale and evidence/provenance trace. The
inspector respects connection/search/status filters. It presents KG evidence, not
workflow execution history. The selected relationship also has its business-label/direction review form so an
authorized owner can resolve ambiguous or needs-review meanings. Confirmation,
rejection and reset use the current KG revision; stale/read-only sessions cannot
edit. Technical join permissions stay independent. Record exploration and
technical permission editing remain hidden in this tab. The underlying services, evidence, review records and permissions remain
unchanged. Inferred labels stay visibly distinct from confirmed meanings.

## Semantic extraction pipeline

1. Structural discovery supplies FK/reference candidates and field mappings.
2. Bounded evidence packages contain dataset names, field names/types,
   PK/FK constraints, descriptions and concept mappings. Credentials, business
   records, default values and arbitrary DDL are not sent to the extractor.
3. The configured structured model proposes a predicate, direction, rationale,
   alternatives and evidence IDs, or an explicit null predicate when ambiguous.
4. Deterministic validation rejects invented/missing relationship IDs, unsupported
   evidence references, generic labels, unbounded output or model confidence
   claims. Every linking-field ID and both dataset IDs must be cited.
5. Durable, leased, owner-scoped jobs publish only against unchanged evidence and
   current authority. Model output is always inferred, never automatically verified.
6. Owner reviews preserve their evidence basis. Changed schema/descriptions or
   mappings require review; regenerated proposals cannot re-confirm an old review.
   Legacy reviewed labels retain a recorded metadata evidence basis too.

There is no Northwind/domain-specific verb replacement table. FK validity and
record key matches do not prove business semantics. Numerical confidence remains
null because no calibrated score is implemented.

The metadata worker automatically detects changed/new relationships after normal
profiling/graph refresh. Unchanged evidence reuses proposals. Batches contain at
most 24 relationships and 48 KB evidence; one model request has a 45-second
client timeout. Stale claims cannot publish. Failed inference needs an explicit
retry, avoiding repeated unbounded billing.

### Authorized live model activation

The owner explicitly authorized automatic schema-only extraction on 18 October
2026 to `api.openai.com`, using the configured `gpt-5.6-luna` model. The existing
`BUILDER_KG_SEMANTIC_INFERENCE_ENABLED=1` setting is now enabled for the Builder
API and worker. Both job/request and provider boundaries still require that flag.

The authorized input includes dataset/field names and types, key constraints,
descriptions, concept mappings and relationship mappings. Business records and
credentials are excluded from model input. Proposals remain inferred; owner
confirmation and technical join acceptance are independent.

Automatic approval review initially blocked the transfer without explicit
payload/destination authorization. The owner subsequently supplied that approval;
no bypass or broader data-transfer scope was introduced. Changing the configured
destination or input scope requires separate authorization.

Structured extraction follows the official [Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).

## Retained record service

The existing bounded, validated actual-record API remains compatible, but its
exploration form is not displayed in the Knowledge graph tab. No record reads
are required to display, filter or regenerate the graph.

## Workflow planning

The existing owned inverted index now reads this semantic KG. Confirmed predicates
receive stronger retrieval weight; inferred predicates are weaker discovery hints.
Ambiguous/stale/rejected meanings are excluded. Selected sources retain only
executable declared/accepted technical paths. Overview retrieves relevant metadata automatically before model generation. The
planner selects the required execution sources from its bounded candidate pool;
saved workflow metadata retains source-selection reasons and semantic evidence.

The planner receives the selected concepts, semantic evidence, source fields,
registered tool schemas and existing connector context. Specialists receive their
explicit task source scope. Generated database workflows pin relevant semantic
edges; changed meaning/status/evidence requires regeneration/review. Existing
technical source checks, Registry authorization, CRUD policies and approval gates
remain independent. Legacy workflows without semantic scope keep their original
validation behavior.

The existing 20-connection, 100-dataset-per-profile and four-source execution
bounds remain. Index retrieval narrows saved metadata; it does not query hundreds
of live databases to choose sources. Tests cover a 154-dataset saved catalog.

## UI acceptance

- Open Data Intelligence → Knowledge graph; record/edit panels must be absent.
- On desktop, select nodes/edges and inspect source metadata and evidence traces.
- Select each connection and All connections; cross-database links appear only
  in the combined view. Use entity/relationship/source search and status filters.
- Click Regenerate KG to queue a rebuild from discovered metadata. Existing
  automatic inference processes changed evidence; unchanged proposals are cached.
- Configure per-connection automatic refresh and save its interval/enabled setting.
- Generate a workflow from Overview with one prompt. Relevant sources/tools are
  selected automatically; inspect their evidence in the saved workflow. The KG
  display filter does not alter backend workflow-creation context.

No Praxi files, existing procurement flow, Google credentials or database write
policy are changed by this feature.
