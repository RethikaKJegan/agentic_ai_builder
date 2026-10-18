# Original-plan Phase 3: prompt-based source selection and reads

This completes the source-selection layer of the final Atlas + Supabase six-phase
plan. Historical query pushdown/federation/job phase numbers describe the existing
read engine and do not imply CRUD or workflow integration is delivered.

## Behavior

Open Data Intelligence → Questions. Enter a question, create a query plan, inspect
Selected sources and the highlighted graph subset, then explicitly run the read.
Selecting a dataset in the graph or dropdown shows its complete source path,
required fields/types, field purposes and relevant confirmed business mappings.
Linking relationships show the exact ordered equality pairs and declared/accepted
review state. Graph links show execution order, not inferred business direction.

Reasons are derived from the validated plan: base/target dataset, output, filter,
grouping, arithmetic, linking or row enumeration. They explain observable plan
usage, not hidden model reasoning or a guarantee that a business interpretation
is correct. The model's overall explanation remains available for user review.
Datasets outside the plan receive no business-data queries from its execution;
planning does inspect the bounded owned metadata catalog.

The planner now receives confirmed current business mappings for supported owned
dataset/field IDs. Suggested, rejected and needs-review mappings are excluded.
Entity names are untrusted metadata and may be ambiguous; they never authorize a
join, grant a tool or replace permissions. Declared/accepted relationships remain
the only candidates for validated execution. The catalog retains its 120 KB bound.

Planning performs no new source read and sends no credentials or row values to
the model. Results remain deterministic. A clarification displays no runnable
source preview. Graph/source/review changes reject stale plans before reads;
changes during planning prevent publishing an obsolete plan. Background jobs
retain the original preview through refresh/recovery, rather than rebuilding it
from a newer graph. Legacy plans without preview metadata remain supported.

## Contracts and evidence

`shared/contracts/data-sources/queries-v1.schema.json` adds optional
`selection_preview` to planned responses and `executed_plan` to successful result
responses. Existing model intent and workflow/agent/tool schemas are unchanged.
No new endpoint is added. The UI parses these fields in `api/data-queries.ts`.

The completed result's Executed logical read plan comes from the server executor,
separate from the review preview. Existing per-source reads, row counts, timestamps,
join checks, native strategy and federated fragments remain the actual execution
evidence. This is structured logical-query evidence; native SQL and MongoDB
pipeline dumps are not exposed. Results returned by jobs remain encrypted with
the existing expiry, ownership and result-size checks.

## Supported limits

This phase preserves existing supported projections, scalar filters, arithmetic,
aggregates and strict many-to-one inner joins. It does not add anti/outer/many-to-
many joins, DISTINCT, arbitrary SQL/scripts, array/nested-field querying, writes,
workflow database tools or EDA/reset. Requests that cannot be represented must
clarify or fail validation; finding customers with no matching activity record is
not newly supported by this work. Source selection is model-assisted and requires
review; schema validation alone does not prove semantic relevance.

Existing bounds apply: four datasets, up to 500 output rows, 5,000-row application
fallback, supported native execution checking up to one million rows/dataset,
bounded dimensions/intermediates/transfers, plan expiry and job deadlines.
Separate databases have independent snapshots. Budget and strict relationship
failures do not return partial totals as complete answers.

## Manual UI acceptance

Use a dedicated linked test dataset with known expected results. Questions and
field names below must be adapted to your actual catalog; they are not hardcoded
routing rules.

1. Ask a PostgreSQL-only question, such as counting the discovered orders table.
   Verify only the required PostgreSQL dataset appears. Inspect its fields and
   purposes. Run and compare the result and source evidence with independent SQL.
2. Ask a MongoDB-only question, such as listing a supported scalar customer field.
   Verify only that collection appears. Compare values with an independent bounded
   Atlas read. Its metadata coverage warning should remain visible where present.
3. Ask a question requiring both databases using an existing accepted relationship.
   Inspect both nodes, required fields, exact linking pairs and review status.
   Run and compare against independent calculations on a stable demo dataset.
4. Confirm an isolated business mapping in Relationships, then plan a question
   using that concept. Inspect the selected source's confirmed concept. Rejected,
   suggested or structurally changed mappings must not appear as confirmed context.
5. Ask an ambiguous measure without a definition, or request an unavailable join.
   Expect clarification/validation failure, never a fabricated result. Confirming
   an entity alone must not turn an unreviewed relationship into an executable one.
6. Plan, then change a relevant test mapping/review and try the old plan. It must
   fail as stale. Replan normally; no source reads should be performed by planning.
7. Submit a background job, refresh and reopen it. Its selected source preview
   must remain attached to that job. Existing cancellation/expiry behavior remains.
8. Repeat on desktop/mobile. Source selection, diagram keyboard controls/dropdown,
   field details and evidence must remain usable without document-width overflow.

Fresh checks, exclusions and workspace-only deployment status are recorded in
`openspec/changes/prompt-source-selection-phase3/verification.md`. Browser API
fixtures establish UI behavior, not live model routing or cloud query correctness.
