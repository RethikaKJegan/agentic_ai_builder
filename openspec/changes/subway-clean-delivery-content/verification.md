# Verification — 12 November 2026

## Actual payload fix

The earlier frontend cleanup changed only rendered previews. The former backend formatter still prepended Demo data and preserved Demo Supplier names in actual generated output. This follow-up removes those insertions and normalizes visible report fields before persistence and downstream binding. Email subjects/bodies, Calendar summaries/descriptions and spreadsheet report titles/tab labels/cells receive clean business text. Supplier display names use Supplier N. Repeated known dataset/policy boilerplate is removed; actual coverage, missing evidence, financial figures and separate currency groups remain accurate as concise notes.

Subway demonstration tool input resolution also cleans supported delivery content before registered-schema validation and exact approval. This covers a future delivery bound to old prepared content. Recipients, mail/thread/resource IDs, Calendar dates/timezones/attendees, spreadsheet project/creation keys and source references remain unchanged. Stored report/assessment/query provenance, original datasets and ontology are not rewritten. Historical/non-Subway content is unchanged. Existing exact approvals cannot authorize a different payload; no mutation is made at dispatch after approval.

## Captured connector evidence

Five focused tests passed through the real runtime binding/params path and real Gmail, Calendar and spreadsheet-report connector code with offline Google transports. Evidence includes decoded plain-text and HTML MIME bodies, Calendar JSON, workbook/tab names, spreadsheet numeric cells, unchanged destinations/dates and cross-tenant non-application. Exact source identifiers and source-reference arrays remain untouched.

The actual saved Subway report from `run_fa4bec3e3e1b47ed87c3464cce3a3002` was replayed locally through final input resolution and all three real connectors with offline transports. Its email MIME bodies, Calendar description and spreadsheet payload contained no demonstration wording or limitation headings; source citations and original figures remained. Zero external actions or model calls occurred in this replay. This verifies payload construction, not live Google delivery.

## Final acceptance and deployment

Final affected acceptance: **75 passed**, covering report preparation, normal Subway runtime/recurring execution, Gmail/Calendar, real offline connector payloads and changed-payload approval rejection. This final run used the checkout with the identical deployed implementation; it is not claimed as an additional isolated-candidate run. An earlier isolated run exposed the two legacy-context failures described below; both were fixed and the complete final affected packet passed.

Only `agentic-builder-subway` restarted, at **21:00 IST**. Effective source: `.local/subway-clean-delivery-release-20261112/app`. Release SHA-256: `7e747f38d4e4df5d138db769cc14f03733674bae847d32e244143eace4e38383`. Consistent backup and rollback override were prepared first. Authenticated public HTTPS session, tools, worker health and query availability returned 200 with no model or external action. Final prior-row, source/ontology/data/receipt/schedule/key/hash and unrelated-service preservation checks passed. The lifecycle registry value is identical; its routine startup updated_at refresh is normalized, as are source-profile timestamps. Frontend and Simpson PIDs remain unchanged.

## Additional verification and boundaries

- Wider isolation/lifecycle/ontology/adaptive/evaluator/usage regression suite: **119 passed** on the isolated candidate before the final defensive legacy-context lookup fix. No evaluator, usage or ontology implementation was changed.
- Canonical contracts, generated UI-contract comparison, scoped strict OpenSpec and whitespace checks passed.
- Initial connector fixtures lacked required inferred provenance, resource directories and Calendar timezone; these were corrected without relaxing any validation. The final five-test run passed.
- The first wider acceptance run had 73 passes and two failures in source-free content-link verification: a legacy optional-context lookup raised KeyError. The final implementation safely reads optional context and explicitly scopes report cleanup to Subway.
- A genuine configured-provider assessment rehearsal failed before report generation because its planned assessment query selected extra fields instead of the required native ID alone. It is retained as failed evidence; assessment prerequisites were not relaxed.
- Automatic approval review rejected an additional live-provider rehearsal because it could send workflow-derived content to an external model provider without specific payload/destination approval. The saved-report offline replay above was used instead. No workaround made that rejected model call.

Previously sent email, existing external events/files and already-completed audit records are unchanged. Start a new run for newly prepared clean delivery content. A legacy pending exact approval may require ordinary fresh review if its content changes.

Private evidence: `.local/subway-clean-delivery-20261112/` contains payload tests, offline saved-report replay, candidate manifest, regression logs, failed rehearsal, consistent backup and deployment/HTTPS/preservation results. Credentials and operational payloads are not published in this document.
