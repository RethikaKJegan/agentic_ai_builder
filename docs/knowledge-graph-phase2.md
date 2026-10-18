# Knowledge graph: Phase 2

The business graph is now called **Knowledge graph** in the UI, including search,
zoom, details and loading/error text. Legacy `/data-ontology` endpoints and stored
review identifiers remain compatible with existing clients and saved reviews.

## Try it in the UI

1. Open **Data Intelligence → Relationships → Knowledge graph** to inspect the
   business entities, arrow labels, source mappings and evidence. Confirm only
   mappings and relationships that reflect your data.
2. Open **Overview** (`/app`) and enter a workflow description.
3. Click **Preview sources and tools**. Clicking Generate without a preview also
   prepares this preview first, without calling the model.
4. Inspect connection/dataset coverage, selection reasons, fields, operations,
   configured tools and the selected graph. Click a graph node to highlight its
   neighbors; the path list shows the exact linking field IDs.
5. If matches are ambiguous or exceed four sources, choose the intended source
   checkboxes and click **Refresh source preview**. This records explicit IDs,
   not user-supplied metadata or permissions.
6. Click **Generate workflow** after reviewing the selection. A metadata change
   between preview and generation requires a fresh preview. A generated plan
   retains its retrieval evidence under Workflow details.
7. Validate, review and publish through the existing controls. Runtime source,
   query, write-policy and approval checks continue to apply.

Northwind examples for the supplied split:

- `List products with their stock and reorder levels.` — expect Supabase products.
- `List categories with their descriptions.` — expect Atlas categories.
- `Review products with their category names, supplier company names, stock and
  reorder levels. Prepare an email summary for my review.` — expect products,
  categories and suppliers when their reviewed/declared linking fields support it.

These prompts do not authorize sending mail or creating events. Recipient/time
setup and any required approval remain visible in the generated draft.

## Implementation

`workflow_api/kg_retrieval.py` maintains owned source documents and an inverted
term index in the Builder database. It contains saved metadata only: dataset/field
names, descriptions, confirmed concept mappings and confirmed business predicate
labels. It never reads business records, opens cloud connections, stores source
credentials or calls an embedding/model service.

The cache revision covers connection generations/status, metadata revisions,
graph jobs/revisions, description/entity/relationship reviews and database write
policy. On the next preview or generation, changed revisions rebuild the index;
unchanged automatic metadata checks reuse it. Connection ownership is applied
before indexing and in every lookup. Disconnects disappear on the next lookup.

Retrieval tokenizes camel case, underscores and simple English plurals. Weighted
matches distinguish dataset/concept names from field references and source paths.
It returns up to 12 ranked candidates plus explicitly selected or connecting
sources, capped at 16 displayed candidates. The planner receives at most four
source definitions. Equal alternatives require source selection. This is lexical
retrieval: synonyms need useful descriptions or confirmed concepts; it is not
unrestricted semantic reasoning.

Selected seeds can add intermediate datasets through declared/accepted technical
paths of at most three hops, still inside four sources. Confirmed business labels
provide meaning; they never make a suggested technical join executable. Missing
paths, stale graphs and incomplete discovery are explicit warnings. Current query
validation decides whether an operation can execute.

The authenticated `POST /knowledge-graph/preview` is metadata-only, with the
additive `knowledge-retrieval-v1` response contract. Caller catalogs, retrieval
evidence and tool definitions are replaced by trusted server state. The planning
resolver reruns retrieval and checks the reviewed revision. Model-proposed source
IDs are checked against the shortlist, then pinned as the existing database scope.
Database specialists receive explicit task source references; an ID outside the
workflow scope is rejected. The master may receive the selected full scope.

Configured tools are drawn from the actual Registry and runtime connectors. Their
appearance in a preview is not an authorization grant. Saved proposals retain
reasons and paths; the normal current-authority and publication/runtime checks
remain the execution authority. Generated IDs include the retrieval revision so
a refreshed KG request cannot accidentally reopen an older unrelated proposal.

## Bounds and limits

The old full-catalog planning limit of 64 sources is bypassed by indexed retrieval,
not by sending more sources to the model. Native regression fixtures verify
154 saved datasets and a one-source model context. Discovery still has the
existing 20-connection, 100-dataset-per-profile, 1,000-field and 2 MB snapshot
bounds; this release does not claim arbitrary numbers of cloud connections.
The index covers successfully discovered metadata, not undiscovered databases.
Broad terms are bounded at 2,000 matching index entries and report truncation.
Large field selections still require a smaller source scope. Runtime cannot
silently expand beyond the reviewed/published source scope; preview again when
additional sources are needed.

No spreadsheet export setup, cloud write permission, credential configuration or
Praxi file is changed by this feature.
