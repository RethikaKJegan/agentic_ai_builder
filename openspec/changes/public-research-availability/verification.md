# Public research verification

The saved Simpsons run `run_b12ab2c233d448e4a609ac22368a5212` completed
query `dqj_7d49b5a78cd0468bba3c2e3b263f278e` but included only query planning,
internal query execution, search-text preparation and report preparation. It did
not contain a web-search action. The tenant opt-in was already enabled, but its
registered tool definitions inherited `needs_configuration` from templates.

The public-research configuration now creates enabled definition copies and uses
the same definitions for installation. Default templates are unchanged. Tests
cover Simpsons, Subway and an arbitrary third client, fresh-copy isolation, schema
compatibility, private identifier rejection and search-to-page provenance.

- Regression suite: 70 passed, including 10 subtests.
- Routing, knowledge-only and final research regression suite: 55 passed (overlaps
  the regression suite).
- Focused final rerun: 12 passed (overlaps the regression suite).
- Shared schemas and fixtures: valid.
- Real public searches and SHA-256-verified HTML/text page retrieval succeeded for
  engine troubleshooting and food cold-chain guidance. These were public reads;
  no internal records were submitted as search text.
- Public authenticated health/scope checks passed for all three accounts.
- Hosted model planning passed for both Simpsons and Subway: public-research
  requests returned prepared proposals containing `tool.supplier_web_search` with
  the correct tenant scope. Those verification drafts were not executed. A first
  web-only check exposed routing into knowledge-only handling; explicit composed
  research routing guidance resolved it in the subsequent hosted checks.
- Stored credentials, existing history counts and complete automation documents
  were preserved. Frontend build unchanged; all five services active.

Live search providers and individual sites can still reject or time out. Those
failures remain explicit; prepared search text is never evidence of retrieval.
Existing approved workflows are immutable and must be regenerated to add search.

Private backups, scripts and verification receipts are retained under
`.local/public-research-availability-20261111/`.
