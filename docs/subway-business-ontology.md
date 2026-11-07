# Subway source onboarding and business ontology

Current ontology: `bov_subway_dump_v4`, with 54 concepts (52 supplied collection
concepts and two modelling parents), 67 relationships and 13 applicable code-derived
rules across nine modules. New planning uses package revision 4 and the full-data query capability.
Filters, counts, totals and scalar left joins now use complete relevant data; display
limits are pagination. See [full-data evidence](subway-full-data-evidence.md).
All 52 historical inspection readers remain available for older workflows. See [dump-grounded ontology](subway-dump-grounded-ontology.md) for the
exact collection/model/service mappings and actual-record relationship checks.
Unconnected code-only models remain only in historical versions, outside new planning.
The archive-only version described below remains available for historical workflows.

Subway retains its existing login, workspace `client-subway` and owner
`subway-client`. Simpsons keeps its separate identity, store, sources and ontology.
No Simpsons records or definitions were copied.

## Sources and restore

Both supplied archives were inspected directly in the project. They contain
MongoDB BSON with per-collection Extended JSON metadata, not SQL databases.

| Archive | SHA-256 | Original collections | Business collections restored |
| --- | --- | ---: | ---: |
| `central-prod_dump_20261030_203002.tar.gz` | `fa0c90984db1fb5ccde41dd80e100e58b6ce4fe3bc2aaf7912e933e4c9b51429` | 35 | 23 |
| `finance-prod-new_dump_20261030_203059.tar.gz` | `2b17ef6f5e0916b4c64ecd8c94cac8d99380ea3ce9518976ffda4e5e608ee2ff` | 36 | 29 |

The restore has 1,218,822 records across 52 collections. Private member hashes,
original schema metadata, analysis, reference probes and the restore receipt are
under `.local/tenants/subway/onboarding/`. Original archives remain unchanged.
Analysis counted BSON records and profiled up to 200 records per included
collection in archive order, not randomly. Platform metadata uses its existing
25-record collection samples. Samples do not establish completeness or prevalence.

The derived databases `subway_central` and `subway_finance` live in a separate,
authenticated MongoDB service on `127.0.0.1:27028`. The application's reader has
collection-level read privileges, with no writes or other database access.
Authentication records, tokens, secrets, raw emails, logs, counters and user-profile
collections were excluded. Secret-looking fields were removed recursively.
Source indexes were recreated without expiry settings that could delete snapshot
records. MongoDB Extended JSON was parsed with BSON-aware decoding.

Two GRN documents and six purchase orders had invalid UTF-8. Their derived copies
use replacement characters; originals are preserved. The successful receipt counts
sanitization performed in that attempt; previously completed collections were
reused after exact row-count checks during interrupted restore recovery.

## Business model and evidence

Nine modules cover organization/legal entities, stores/distribution, procurement,
budgets, receipts/invoices, operational approvals, smallwares, performance/balances
and document/report evidence. Fifty-four concepts span five layers: 52 source-record
concepts and explicit Object/Business record modelling conventions. A receipt record
is distinct from the business event; the `assets` collection represents observed
attachments, without asserting physical fixed-asset ownership.

Eleven candidate references were checked against native target identifiers using
up to 200 records each. Ten matched 200/200; approval stages matched 189/200.
MongoDB declares no foreign keys here. Overlapping integer IDs and missing references
remain unresolved. These descriptive candidates grant no executable join authority.

The two legal company records remain distinct within the user-designated client
archive scope. The dumps do not establish brand allocation rules. AOP, UEM,
weekly balance calculations, approval thresholds and status transitions require
authoritative documentation. No business policy rules were invented or verified.

Versioned definitions, source quotations, hashes, module/layer definitions and the
knowledge package are saved in `ontology/subway/`. The existing offline OWL/RDF and
SHACL compiler passed definition and shape validation. Instance conformance,
OWL reasoning and business-policy verification are explicitly not claimed.

## Platform integration and limits

The sources are pinned as `dbconn_subway_central` and `dbconn_subway_finance`.
A dedicated adapter verifies source ID, database, endpoint, port and credential URI
fingerprint. Existing cloud-connector endpoint policy remains intact. Startup rejects
foreign workspace/owner state and unexpected source bindings. Reads recheck current
ownership, metadata revision and source generation. MongoDB separately denies writes,
other databases and excluded collections.

The existing source browser, ontology interface, planning evidence retrieval,
Registry, action planner and graph runtime are reused. The server automatically
supplies Subway's immutable package `subway-business-v1`, revision 1, to normal chat
planning. Its 12 read capabilities use the existing workflow-bound package connector.
Browser input and model output cannot substitute another tenant or source endpoint.

Package capabilities return up to 25 projected records in native ID order. They
support bounded evidence summaries, not arbitrary filters, exhaustive reports or
population totals. The normal source browser supports paging through all restored
business collections; existing query features retain their normal validation.
This is an archive snapshot, without ongoing production synchronization. No
Subway-specific operational case templates or email/Google integrations were added.

Ontology documents and regeneration use Subway's module catalogue and preserve its
workspace, layers and sources. The Simpsons reference import is hidden for Subway
and rejected by backend source binding. Model regeneration only occurs after an
explicit user action; onboarding and verification made zero model calls.

## Preparation and verification

`scripts/onboard_subway.py --directory <new-private-directory>` creates a staged
application store from an auth-only Subway store and the existing restore receipt.
It refuses overwriting a prepared directory or existing source connections. It
never switches a running deployment. Archive extraction and restore scripts likewise
preserve original archives and use private staging.

Staged verification exercised all 12 mapped reads and completed a bounded store
read through the actual action-plan compiler, Registry and runtime, with zero model
calls. Live AI chat remains for the user's own test, as requested. Release evidence,
backups and regression results are recorded in the OpenSpec onboarding change.
