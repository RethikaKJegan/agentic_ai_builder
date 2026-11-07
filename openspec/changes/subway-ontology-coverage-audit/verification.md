# Subway ontology coverage audit verification — 6 November 2026

## Result

Deployed immutable ontology `bov_subway_audited_v3` and package revision 3:
158 concepts, 156 relationships, 28 descriptive non-executable rules, 26 modules,
52 collection-read capabilities and 637 field mappings. The previous enrichment
was selected coverage; the full audit and remaining limits are documented in
`docs/subway-ontology-coverage-audit.md`.

The audit inventories 527 source files: 156 declared business-model files, 63
infrastructure/security files, 10 schema/helpers and 298 services. All 156 business
models map to one represented concept. Exact member/declaration/ref quotations and
hashes are retained. Same-service reference resolution leaves 111 explicitly unresolved
references, principally excluded User/Person identities and three unmatched model names.
No identity aliases or executable joins were invented. All eight original archive hashes
were rechecked by staging and installation.

## Evidence

- 121 affected backend tests passed: audit, Subway code ontology/onboarding/auth,
  Simpsons isolation, business planning/composition and connected action plans.
- 23 final focused tests passed: coverage audit and ordinary business source behavior.
  These suites overlap and are not a distinct-test total. The focused suite includes
  the final sample-coverage annotation change.
- Shared schemas/fixtures passed. Strict OpenSpec validation passed. `git diff --check`
  passed. No frontend code changed in this audit.
- Actual counts in all 52 restored collections match the original restore receipt:
  central 311,097 records/23 collections; finance 907,725/29; total 1,218,822.
  Source metadata has 2,314 fields including nested and unsupported types; the 637
  projected scalar mappings do not claim all-field coverage.
- All 76 actual package reads succeeded: revisions 1/2 each have 12; revision 3 has 52.
  Empty blogprojects returns zero; larger blog projections return fewer complete
  records to preserve evidence limits. No source writes were performed.
- A staged controlled-planner workflow received revision 3 context and completed an
  actual bounded source read through preparation, Registry and runtime. No external
  model calls, outgoing actions or source writes were performed.
- Five representative questions find the expected saved rule. Four failed to return
  that rule in the previous retrieval implementation (two returned no match). All
  156 represented models and 28 rules were retrievable by saved name: 184 lookups,
  zero failures. This does not verify arbitrary phrasing or live-model quality.
- Compile/OWL/SHACL definition validation passed. Instance validation, exhaustive
  rule interpretation and policy approval were not performed.

## Corrected failures

The audit caught and corrected report fields rejected solely for containing spaces,
missing source identities for an empty collection, oversized evidence from larger
projections, the mistaken application of a 16-action execution limit to a 52-operation
catalog, missing model coverage and missing rule-only module selection. Tests cover
array refs/comments, old/new immutable bindings, wrong owners, binding mutations,
new records in the empty collection, byte bounds, default package size limits,
catalog cycles and the unchanged 16-task execution bound.

## Deployment and preservation

The operator installer creates a private SQLite/environment backup, verifies current
head still equals reviewed revision 2, rechecks source hashes and staged compilation,
then appends v3/documents/compilation/package in one transaction and updates only
Subway's configured default package revision. It does not copy staged smoke workflows
into production or replace the live SQLite file. Only Subway's backend was restarted;
Simpsons and the shared frontend were left running.

Pre/post fingerprints and live endpoint/browser results are recorded under
`.local/tenants/subway/coverage-audit/`. `release/` holds the backup, installation
receipt, public browser screenshots and live verification. Original workflows/revisions,
runs, Google accounts, earlier documents/versions/packages and credentials are preserved.
Historical ontology versions and package revisions 1/2/3 remain available. Foreign
source IDs return 404 in both directions. Both client logins and ontology pages are
checked on desktop/mobile, including Subway rule citations and its own questions.

Private receipts:

- `restored-count-verification.json`: complete restored counts and metadata comparison.
- `retrieval-verification.json`: before/after questions and 184 definition lookups.
- `stage/workflow-verification.json`: 76 reads and controlled workflow completion.
- `tests-final.log`, `focused-final-tests.log`: passing regression logs.
- `preservation-before.json`, `release/live-verification.json`: preservation checks.
- `release/browser-verification.json`: public desktop/mobile checks.

Rollback selection: stop Subway, set its `BUILDER_SUBWAY_PACKAGE_REVISION` to 2 and
restart. Earlier immutable providers remain available. Restoring the full backup
requires a stopped service and review of subsequent changes, because it discards them.

## Remaining boundaries

104 classes are code-only, with no connected records in these two dumps. The 28 rules
are selected reviewed guards; all 960 service throw sites have not been interpreted as
business policy. Scalar projections and bounded samples cannot answer every field,
filter, aggregate, join or application action request. Such questions must identify the
specific missing dataset/operation/policy rather than invent answers. Live model chat
is left for the user's own test as previously requested.
