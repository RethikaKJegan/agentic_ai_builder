# Verification — 11 November 2026

The saved run `run_7cedf362200b4b33a49125044176812e` completed its query and
content preparation, then blocked at the spreadsheet approval node with
ACTION_INPUT_INVALID. Its content output had a tab with rows=[]; the pinned spreadsheet
input requires at least one row. The zero-match grouped query itself succeeded.

The correction derives server-owned report context from actual downstream tabs
bindings and tool contracts, plus completed verified direct query dependencies. Only
when every direct query dependency has complete, unpaginated zero-match aggregate
evidence may empty generated tabs be rendered as an explicit report-status table.
The status table has no invented category, count per category or numeric average.
Nonempty rows are preserved; incomplete/unverified/mixed nonempty inputs are not
converted to no-match output. Empty generated tabs without verified empty evidence
remain invalid rather than fabricating a result.

Model response formatting uses the downstream tabs contract where consumers agree;
unique-header validation remains at the trusted boundary even though the provider
transport omits unsupported uniqueItems. Content validates downstream tab limits
before persistence/tool dispatch. Existing row-width, source-reference and URL checks
remain. No tool permission, source query, approval gate or effect identity is changed.
The injected context preserves existing data keys to avoid changing working reports.

Actual copied-run replay confirms the old tabs fail the pinned spreadsheet schema,
then normalizes a copy of the report, preserving summary and citations. The corrected
tabs pass that exact schema. No live query, model or provider is invoked for replay.

A controlled end-to-end graph test runs a zero-match grouped query, produces the
same empty table shape, normalizes before approval, creates one sheet and sends one
email through controlled providers with verified receipts. Tests also cover preserved
nonempty data, incomplete/unverified/mixed evidence, early invalid-table feedback,
provider schema bounds and unchanged canonical output schemas. Existing nonempty
query/Sheets/email, Calendar, web research and percentage tests form the regression run.
Final counts and hosted preservation checks are recorded in deployment.md.

No live paid model, source query or email/Sheets/Calendar action is performed for
verification. Old failed runs remain historical; no schedule is activated or replayed.
Unsupported or invalid content still stops safely. This fixes the evidenced empty-row
contract mismatch; it does not guarantee every future model output is valid.
