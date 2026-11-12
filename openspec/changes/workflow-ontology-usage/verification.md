# Workflow ontology usage verification

New connected plans pin an authorized ontology version, mapping identities and
exact query field IDs. Runtime action instances retain verified query/record usage
through existing signed workflow metadata and run JSON. The existing authorized
knowledge inspection endpoint exposes normalized explicit mappings for both native
knowledge packages and imported collection bindings. No source labels or concept
names are used to infer usage. No historical data is backfilled.

The frontend prefers the new pin, highlights mapped source reads in green and
shows field/query explanations and an executed concept count. Missing provenance
is stated above the graph. Current-version fallback remains exploration only.
Completed report consumption is separately recorded; email/Calendar/Sheets actions
do not inherit ontology usage. No new schema migration or provider calls.

Validation so far:
- 60 existing connected-plan/query backend tests passed before the mapping-format extension.
- 59 mapping/knowledge/API isolation tests passed, including a new imported-binding test.
- Saved-plan/runtime/public-view integration passed with the actual controlled CrewAI runtime.
- 27 focused frontend adapter/map tests passed.
- Final isolated production build, TypeScript, changed-file ESLint, shared contracts,
  strict OpenSpec and diff whitespace checks passed.
- Six production-artifact browser journeys passed: three tenants × desktop/mobile.
- Full frontend suite: 593 passed across 88 files with two workers. An earlier
  high-concurrency run had one orchestration timing failure; its 22-test isolated
  rerun and the complete reduced-concurrency rerun both passed.
- Read-only hosted metadata: 45/47 native Simpsons mappings and all 636 normalized
  Subway bindings match exact source fields. Missing or ambiguous mappings remain unavailable.

Deployed after explicit user approval. Public checks passed for all three accounts;
normalized mapping responses and cross-account denial passed. Four hosted browser
journeys passed across Simpsons and Subway on desktop/mobile. Protected counts,
configuration hashes and the active artifact were verified. No workflow was run.

Deployed artifact build: VNy3gW78UlZKNdEehD57j. Private release
preparation is under `.local/workflow-ontology-usage-20261111/`.

Limits: field access is evidence of query usage, not proof that any matching record
or business conclusion exists. A query with zero matching rows may highlight its
mapped input fields. Concept endpoints never establish relationship/join usage.
Older workflows without pins remain qualified; new workflows are required for the
new persisted tracking. This change covers the standard workflow_data_query reader
and native mapped-record readers; unrelated query providers keep existing behaviour.
