# Final deployed Subway ontology audit

Current query path: [complete Subway data evidence](subway-full-data-evidence.md).
New workflows use full relevant data for filters and aggregates. The 25-row package
readers discussed below remain historical inspection tools, outside the default new
query selection. The app-property numeric/string link is now resolved from its schema.


Date: 6 November 2026. Audit performed against the current deployed v4 and a fresh
private copy of the live Subway application store. No application code/configuration,
production workflow, credentials, ontology versions or source data were changed.
No external model calls, outgoing business actions or service restarts were used.

## Result

No new defect was found within the checked scope. Deployed snapshot matches the
reviewed `bov_subway_dump_v4` artifact and passes offline definition compilation.
It contains 54 concepts (52 supplied collections plus two parents), 67 qualified
relationships, 13 applicable descriptive rules, nine modules and 52 collection readers.
The 104 code-only classes remain absent from new planning. Historical pins are intact.

## Fresh checks

- All 13 representative business questions retrieved the expected rule and exact
  matching source quotations/hashes. Questions cover budget approval, independent PO
  department, ticket/category metadata, linked requisition approval, approval-config
  updates/deletion/manager restrictions, available reservation amount, nonpositive
  budget modification, GRN duplicates, advance ceiling and document confirmations.
  The two task-local external prerequisites remain explicitly supplied in context.
- All 52 collection definitions and 13 rules were retrievable by saved label:
  65 lookups, no failures. This tests saved-definition discoverability, not arbitrary
  natural-language paraphrases or generated response quality.
- All 128 current/historical package reads succeeded using actual restored Subway
  data and freshly initialized provider bindings in a private copy of the live store.
- A new controlled-planner workflow completed through preparation, Registry and
  runtime with v4, 54 concepts and no code-only concepts in planner context. The read
  used actual Subway data. No live-user workflow was executed or model provider called.
- All 67 relationships were rechecked against bounded native IDs: 57 matched all
  sampled values, two partially matched, eight had no observed scalar references.
  The existing qualifications remain accurate; these checks do not authorize joins.
- All 52 restored collection counts still match: 1,218,822 records in total.
- 15 focused tests passed: dump grounding, Subway auth and Simpsons isolation.
  Exact code/member hashes, service correspondence, source citations, array paths,
  owner checks, historical bindings and task-local prerequisites are covered.
- Both clients passed public login and ontology checks at desktop and mobile sizes.
  Subway rule citations and its own questions rendered; no page errors or horizontal
  overflow. Live APIs show the expected v4/counts/compilation/historical revisions,
  and actual foreign-source IDs return 404 in both directions.
- Before/after client fingerprints preserve workflows/revisions, runs, Google accounts,
  metadata snapshots, prior versions/packages/documents and credential files. Simpsons
  keeps its existing ontology and backend PID. Both backends and frontend were active.

## What this establishes for a user request

For the tested questions and available supplied collections, the deterministic
ontology-to-planner-to-reader path supplies the relevant code/schema citations and
bounded source records. It avoids globally treating unrelated application models as
missing evidence. The audit supports this defined scope; it is not a guarantee that
any future question can be answered completely.

Specific source limitations remain: two partial reference samples, eight unpopulated
reference samples, empty records, sampled scalar projections and two rule-local absent
prerequisites. Package reads return at most 25 complete records and can return fewer
under byte limits. These sample reads do not establish exhaustive totals, arbitrary
filtered result sets, automatic joins or authority to execute business actions. Code
rules remain descriptive and non-executable; not every service branch is formalized.
An actual use case needing those operations or absent facts must identify that precise
requirement rather than invent an answer. No live AI answer quality claim is made;
the user previously chose to test chat themselves.

Private receipts under `.local/tenants/subway/final-ontology-audit/`:
`evidence-matrix.json`, `workflow-verification.json`, `source-probes/`, `tests.log`,
`live-verification.json`, `browser-verification.json` and preservation fingerprints.
The fresh copied store and browser screenshots are private. No secret values or raw
record contents are included in this report.
