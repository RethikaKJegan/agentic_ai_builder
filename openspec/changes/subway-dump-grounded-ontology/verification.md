# Dump-centered Subway ontology verification — 6 November 2026

## Deployed result

`bov_subway_dump_v4` and package revision 4 are active for new Subway planning:
54 concepts (52 restored collections and two modelling parents), 67 relationships,
13 applicable descriptive non-executable rules, nine modules, 52 bounded collection
reads and 637 scalar mappings. All 104 unconnected code-only classes are excluded
from this active snapshot and package. Historical versions/packages 1–3 remain
immutable and accessible for prior workflow pins.

All 52 collections map to an exact source model with archive/member hashes and
export correspondence. Direct model/export-symbol service usage was found for 48.
Four have model/schema evidence but no direct service call: central.plaops,
central.pluems, central.appproperties, finance.reportfiles. Imports alone are not
asserted to be business execution. Service references and exact short quotations
are attached where supported.

Thirteen rules are relevant to supplied records. Eleven have all their original
inputs represented. Two preserve guards on available purchase orders/budget lines
but explicitly record unavailable purchase-request/reservation prerequisites on the
specific rule, without adding those unconnected classes or blocking unrelated reads.
Unrelated application rules and a purchase-request-only rule are excluded.

## Relationship validation

Root-schema resolution corrects syntactic ref paths, resolves nested schema variables
and array paths, and ignores unconnected/helper schemas. Exact same-application model
names are required; no cross-service identity guesses were introduced.

All 67 relationship definitions were checked against actual restored data: 57 matched
all sampled scalar IDs, two partially matched (stages.approvalId 189/200 and
apps.properties 4/5), eight had no observed scalar values. Checks are bounded to 200
native-ID-ordered source documents having the field and 1,000 scalar references per
relationship. These are qualified descriptive checks, not global referential integrity
or executable join authority. Overlapping candidate/code definitions are not distinct
joins. All 52 restored collection counts match the original receipt: 1,218,822 records.

## Verification

- 76 affected backend tests passed across dump grounding, prior coverage/code ontology,
  Subway onboarding/auth, Simpsons isolation, business planning and business sources.
- After adding the final two task-local prerequisite qualifications, all five focused
  dump-grounding tests passed again. These overlap the broader suite.
- Compile/OWL/SHACL definition validation passed. No instance-level reasoner or policy
  approval is claimed. Shared contract validation and strict OpenSpec passed.
- All 128 actual package reads passed across revisions 1/2/3/4 (12/12/52/52).
- A staged controlled-planner workflow completed a real read through preparation,
  Registry and runtime, using revision 4. Its planner context asserts 54 concepts and
  zero code-only concepts. No external model calls, source writes or outgoing effects.
- All 52 collection definitions and all 13 rules were retrievable by saved label:
  65 lookups, zero failures. Identifier-only initialApproval and allowConfirm cases
  continue to retrieve their matching rule. No unrelated application classes/rules
  enter the snapshot-derived planner references.
- Both public logins and ontology pages passed desktop 1440×1000 and mobile 390×844,
  with no page errors or horizontal overflow. Subway's 13 candidate rules, source
  quotations and own business questions render correctly.
- Live APIs report v4, 54/67/13 counts, nine modules, compilation passed and all four
  package revisions. Foreign source IDs return 404 in both directions.
- Before/after fingerprints preserve both clients' workflows/revisions, runs, Google
  accounts, metadata snapshots, credentials and all earlier versions/packages/documents.
  Simpsons remains at 79/48/8 and its backend PID was unchanged.
- `git diff --check` passed. No frontend source changes in this correction.

## Deployment

The operator script verifies archive hashes, immutable reviewed v3 baseline, current
workspace head and staged compilation/package fingerprints. It creates a private
SQLite/environment backup, appends v4 and new evidence/compilation/package in one
transaction, and updates only Subway's default package revision. The staged smoke
workflow database is not copied into production. Only Subway's backend was restarted;
Simpsons and the shared frontend were left running. All three services were active.

Public artifacts: `ontology/subway/business-ontology-v4.json`,
`knowledge-package-v4.json`, `dump-code-correspondence-v4.json`,
`dump-relationship-probes-v4.json`, `validation-report-v4.json`.

Private evidence under `.local/tenants/subway/dump-grounding/`:

- `final-with-prerequisites/`: final model/service mapping and actual-record probes.
- `tests.log`, `final-focused-tests.log`: regression results.
- `stage/workflow-verification.json`: final 128 reads and controlled workflow receipt.
- `retrieval-verification.json`: all 65 definition/rule lookups.
- `preservation-before.json`: predeployment fingerprints.
- `release/`: database/environment backup, install receipt, live API preservation
  checks, public browser results and screenshots.

Rollback default: while Subway is stopped, set its configured package revision back
to 3 and restart. Historical definitions/providers remain. Full SQLite backup restore
requires reviewing subsequent user changes because it would discard them.

## Practical limits

All active collections correspond to supplied data. Bounded sampled properties,
missing references, empty records, absent task-specific external prerequisites,
unsupported filters/aggregates/actions and unverified policy can still limit a specific
request. No unrelated code-only application is treated as a globally missing dataset.
Live-model response quality remains for the user's own chat test, as requested.

## Final audit requested after deployment

Repeated on 6 November 2026 using a fresh copy of the current deployed store:
13 realistic rule questions and 65 definition lookups passed; 128 actual source reads
and a new controlled workflow passed; all 67 reference samples and 52 full collection
counts were rechecked. 15 focused grounding/auth/isolation tests and both clients'
public desktop/mobile checks passed. No code/configuration changes or restarts were
needed. Scope and limitations are detailed in `docs/subway-final-ontology-audit.md`;
private receipts are under `.local/tenants/subway/final-ontology-audit/`.
