# Workflow navigation verification — 10 November 2026

Successful Overview generation now opens the existing connected workflow page for
all prepared composition kinds. The URL retains composition, durable Overview
request and selected run references. The workflow page reloads the owner-scoped
request and rejects a mismatched request, composition or owner before displaying
review/action controls. Its existing review retains schedule consent, activation,
pause/resume/cancel, graph, steps, agents/tools, execution and report controls.
Navigation and restoration never approve, activate or execute work.

Overview renders compact progress/clarification feedback and a link for an old
prepared request. Returning to Overview does not automatically reopen that old
workflow. A restored pending request does navigate when it finishes. A late
restoration response cannot overwrite a newer generation.

- Frontend unit suite: 563 passed across 86 files. Final loader/consent subset:
  13 passed, overlapping that suite.
- Exact production-artifact browser suite: 16 passed on desktop/mobile, covering
  recurring consent and reload, one-time/read-only navigation, restored pending
  requests, cancellation, uncertain submission retries and legacy query coverage
  and clarification views. Responses were fixtures; no paid model/provider call.
- Production build, TypeScript, frontend source/changed-browser lint, canonical
  contracts, generated-contract drift, strict OpenSpec and patch formatting passed.
- Broad `npm run lint` also scans retained historical `.next-before-*` deployment
  artifacts and reports generated-code violations. Source lint passed separately;
  those retained rollback artifacts were not modified to silence lint.
- Six hosted desktop/mobile checks passed across all three accounts, with no page
  errors or horizontal overflow. The two Simpsons checks opened and reloaded a
  real existing saved composition through its Overview review URL. Mutations were
  blocked; only GET/HEAD/OPTIONS and the exact read-only Overview `operation=get`
  POST were allowed.
- Authenticated public account checks passed; backend/tenant/worker PIDs stayed
  unchanged. Existing history counts, stored encrypted credentials and configuration
  hashes were preserved, excluding generated Registry metadata.

Private evidence and screenshots: `.local/overview-workflow-navigation-20261110/`.
No live workflow generation, execution, schedule activation, email, Sheets or
Calendar write was submitted during verification.
