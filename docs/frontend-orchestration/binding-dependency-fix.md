# Referenced action dependencies — 5 November 2026

The combined investigation/search/Sheet/email/Calendar draft failed `ACTION_BINDING_INVALID`: “Output binding must name an explicit dependency.” Backend diagnostics show email and meeting content binding to the spreadsheet creation receipt while listing only comparison and spreadsheet verification as dependencies. Creation was a transitive predecessor, but the validator correctly requires the referenced source as a direct dependency. The bounded planner correction retained the same omission.

New automatic goal-mode drafts now materialize direct dependency edges from output, generated and receipt bindings to existing action IDs before validation and fingerprinting. Conditional binding references are included. This does not add actions or grants, alter approved revisions, or bypass receipt verification. Full graph, source schema, optional-source, cycle, budget, permission and exact-payload approval checks still run. Unknown sources and self-references are not converted into valid dependencies. Advanced mode retains its explicit dependency requirement.

Strict dependency failures now include action ID, source action ID and required dependency in bounded planner feedback, without including the referenced data. The generic validator remains strict; only new goal-mode proposals receive normalization.

Tests cover all three reference kinds, idempotent edge completion, a Sheet receipt consumed through a later content-review dependency through actual Registry/CrewAI/GraphRunner and controlled providers, and rejection of unknown sources, cycles, optional sources and advanced-mode missing edges. Private original diagnostics, source rollback copies and verification receipts are under `.local/dependency-fix-20261105/`.

The first combined live draft check passed the previous dependency failure but stopped at `ACTION_AUTHORITY_DENIED`. Its discarded raw provider proposal was not retained, so the exact original offending field is not asserted. Invalid model authority bindings now receive the same single bounded draft correction as invalid schema bindings, with action/target/source metadata. The corrected proposal still passes the unchanged authority validator; a repeated illegal generated recipient remains rejected. Explicit caller-supplied proposals do not receive model correction.

Verification: affected goal/connected suites passed 80 tests. Final targeted dependency and bounded-authority follow-up passed 10 tests, 39 deselected (overlapping coverage, not added to the 80). Shared contracts and whitespace checks passed. Intermediate failures and private source rollback evidence are retained under `.local/dependency-fix-20261105/`. No database migration or frontend build change is required.

## Final deployed verification

The actual configured model generated the combined complaint/search/Sheet/email/Calendar draft `composition_c6d900c6a68aec1cf431941a` through the public frontend. Generation and canonical compilation both returned HTTP 200. The saved proposal has 12 actions, all four requested connector capabilities, no missing inputs, and direct dependencies for every output/generated/receipt binding. It used two planning calls, including the existing one-correction allowance. The selected account’s email resolves the self-recipient.

Public normal-login desktop/mobile checks passed for its visual workflow graph with zero browser errors and failed HTTP reads. Both API and worker source fixes are deployed; API, worker and frontend are active with zero automatic restarts. No frontend rebuild, database migration, Git commit or push was performed. There are zero runtime executions for this draft: no web search, Sheet creation, Gmail send or Calendar event creation was performed. Actual execution and external provider success are not inferred from draft generation.

[Open the verified combined draft](https://praxi.bellcorpstudio.com/app/workflows/investigate?connected=1&composition=composition_c6d900c6a68aec1cf431941a). Existing rejected attempts and previously saved/approved workflows remain unchanged.
