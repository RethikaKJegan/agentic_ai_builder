# Verification — 12 November 2026

The failed run `run_267717eb21874c3a930f6d5b91c98859` completed the registered deterministic assessment and two web searches, then blocked at `prepare_reconciliation_report`. The report step ran for about 91 seconds. Its original wrapper discarded the underlying exception, so the exact historical provider cause cannot be recovered or asserted. The previous assessment query fix is not the cause of this new failure.

The existing runtime now sends Subway assessment report evidence as a reversible dictionary/table transport, with no sampled or deleted outcomes. The original persisted receipt is unchanged. Replaying the actual saved report input through normal runtime binding and CrewAI build reduces its data from 478,112 to 231,418 JSON bytes; expansion exactly equals every original value. This is offline transport verification, not a successful live model report or delivery.

Timeout, connection, authentication, rate-limit, rejected request and provider service errors retain separate typed codes. Unknown model errors remain unknown, with safe exception-class diagnostics. Graph events retain only safe diagnostic metadata, never provider exception messages or response bodies. Recovery directs model failures to model-service diagnostics instead of claiming an evidence/authorization issue. The application never automatically repeats provider calls or pending external actions for these failures. Existing approval and source gates remain intact.

Subway workflow cards use fixed 280×168 dimensions matching their Dagre layout, bounded visible titles, separated dependency edges and readable initial zoom. Original instructions remain in the existing inspector. Other tenants retain the original canvas behavior.

## Automated evidence

- Wider affected backend suite: **102 passed** (controlled provider/external transports).
- Exact isolated backend candidate: **35 passed**, including report transport/provider errors, persistent normal Overview→assessment→report/scheduled occurrence, procurement runtime, Calendar and Gmail regressions.
- Additional model/protocol/report/recovery suite: **31 passed**. Counts overlap and must not be added together.
- Actual saved report input: exact evidence round-trip through normal runtime params and CrewAI task construction, zero model calls, external actions or production application writes.
- Frontend domain suites: **38 passed**. Typecheck, changed-file lint, isolated production build, canonical contracts, generated UI contracts, strict OpenSpec and whitespace checks passed.
- Browser acceptance: **8 passed**, including desktop/mobile long parallel workflows, card non-overlap, readable initial zoom, preserved full instructions and existing Knowledge Map tenant journeys. A final two-case screenshot run also passed; counts overlap. Initial harness selectors used incorrect control case and a non-exact task label; those attempts are not passing evidence.

Private evidence: `.local/subway-report-layout-20261112/`. No Simpson production account, workflow, record, ontology or connection is changed. No paid model call, real email, Calendar event or spreadsheet write is part of acceptance. The old failed run remains historical; future provider availability cannot be guaranteed by an application change.

## Deployment and hosted verification

Only Subway backend restarted at 16:21:54 UTC, followed by the frontend at 16:22:14 UTC. Active source: `.local/subway-report-layout-release-20261112/app`; frontend: its sibling `frontend`, build `HvhsqDX4nygmmxGorO3O8`. Both releases were copied from their exact previously active artifacts with only scoped files overlaid. Manifests and rollback overrides are retained privately.

The public application was verified against the user's actual failed workflow on desktop and mobile. Cards do not overlap, the new layout is present, and recovery identifies a model-service failure while preserving the old run. Authenticated session, tools, worker health and query availability return 200. Browser checks perform only GET requests and have zero page errors. No retry, model invocation, research request, external action or email resend was performed.

Consistent pre-deployment backup and original-row comparisons preserve all original data, ontology, credentials, receipts, workflow history and schedules. Simpson and unrelated service PIDs and their shared source hashes remain unchanged. The exact old provider exception was not recorded by the old code and cannot be reconstructed; these changes reduce transport size and make future failures diagnosable. A fresh live-provider reconciliation report has not been accepted by these checks. No claim that external provider failures can never recur is made.
