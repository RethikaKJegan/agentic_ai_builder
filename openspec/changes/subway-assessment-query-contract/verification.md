# Verification — 12 November 2026

## Generic correction

The failing run requested ten valid purchase-order fields for reconciliation. The assessment previously required its fields list to equal exactly the native-ID field and raised an API error that crossed the runtime boundary as INVOCATION_FAILED.

All eight registered assessment types now validate the entire requested detail query against the current authorized catalog before canonicalizing only its projection to native IDs. Missing/empty projections receive the same identity selection. Filters, hidden-field sorting, offset and limit are unchanged. Unauthorized/unknown/duplicate fields, wrong base collections, joins, metrics, grouping and limits over 20 remain rejected; no malformed query is silently widened. The original input is not mutated, its original input digest remains authoritative, and coverage links requested/effective field lists to the actual query receipt.

Both assessment binding and invocation translate known ApiFailure exceptions to RuntimeFailure with their original code/status. Explicit recovery mappings distinguish invalid queries, authorization, stale metadata, timeout and evidence bounds. Unknown exceptions remain failures. Validation errors are not automatically retried, and uncertain external writes retain their reconciliation requirement. No Registry schema or definition, ontology, policy or source scope was changed.

## Tests and exact failed-input rehearsal

- Focused query/runtime/recurring suite: **23 passed**. Covers all assessment types, extra/missing/empty field projections, filter/sort/page membership, invalid inputs, typed connector errors and complete ordinary/recurring workflow execution. An initial assertion incorrectly named the existing report's ID field; the fixture assertion was corrected to po_id without changing report behavior.
- Exact isolated candidate acceptance: **74 passed**. Includes query contracts, procurement rules/runtime, persistent data/runtime, dataset recovery and the prior actual-delivery cleanup.
- Exact isolated candidate integration/isolation regressions: **96 passed**. Includes Simpson isolation/ontology, Gmail, Calendar, adaptive evaluator, conditional/paginated evidence and usage accounting.
- Canonical contracts, generated UI-contract comparison, strict scoped OpenSpec and whitespace checks passed. Counts overlap and must not be added together.

The exact saved input from `run_eb0cfaf37c7e4e449f8d3ccd45bb0240` was replayed using a consistent isolated application-store copy and genuine persisted Subway records. Ten requested fields canonicalized to one native-ID field, selected all eight purchase orders, and produced a reconciliation report equal to an otherwise identical ID-only baseline. The original input and digest stayed unchanged. A limit-21 negative request surfaced SUBWAY_ASSESSMENT_INVALID through the bound runtime connector. This rehearsal made **zero model calls, external actions, company-source writes or production application writes**. It did not rerun downstream internet search, spreadsheet creation or email delivery.

## Deployment

Only `agentic-builder-subway` restarted at **21:26 IST**. Effective immutable source: `.local/subway-assessment-query-release-20261112/app`. Release SHA-256: `c1d6c24e2f4cb82515b618abf2a23bff76b4cccff030b299ceeefa82e08ca4cf`.

A consistent Subway backup and rollback override were prepared before rollout. Authenticated public HTTPS session/tools/worker-health/query availability returned 200. Final comparisons retained all existing protected source/data/ontology/receipt/schedule/history rows, credentials and code hashes; routine source-profile timestamps and the identical lifecycle registry value's startup timestamp are normalized. Frontend and unrelated backend PIDs, including Simpson, remained unchanged. Only the two implementation files and two regression files differ from the preceding backend release.

Existing failed runs remain historical evidence. Create a new run to use the fix. No live retry, paid provider call, public web search, external delivery, schedule edit or Simpson mutation was submitted during verification. Unsupported queries and genuine operational failures still fail closed with their specific diagnostics; this is not a claim that all possible workflow errors are eliminated.

Private evidence: `.local/subway-assessment-query-20261112/` contains test logs, exact failed-input replay/assessment output, manifests, consistent backup and deployment/HTTPS/preservation checks. Credentials and operational payloads are not published here.
