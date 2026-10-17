# Phase 6 action audit

Current source inventory records every JSX control/handler; loops and delegated primitives are recorded once. Existing Phase 1–5 behavior is preserved and covered by prior suites plus the Phase 6 combined regression run.

| Area | Read/action boundary | Permission and verification |
|---|---|---|
| Run history | GET /runs with workflow/status/date/cursor filters; 50 per page | runs.view + trusted workspace; filter-before-limit, cursor and HTTP tests |
| Selected run | GET exact run + sequenced event pages; serial 3s updates/backoff; terminal stop | exact run/workflow/version identity, event deduplication and transition checks; recovery/terminal tests |
| Approval decisions | Existing explicit POST decision; no replay | workflow.approve + exact gate approver_roles + workspace scope; server eligibility projection; real backend/browser tests |
| Monitoring/readiness | 15s serial GET; bounded triggers/policies; separate cursors | runs.view; active release policy version/scope; source state/preparation/poll health |
| Integrations | Existing configuration check / admin read-only probe | tools.read; authenticated admin for connection verification; no fabricated activation |
| Governance drafts | Browser-only draft edits | server-authenticated admin required for draft UI; role flag cannot grant capabilities |
| Enforced governance | Read-only backend revision evidence | No production policy edit route or button; scope/version displayed |
| Workflow overview | One serial 15s snapshot loop; in-flight coalescing | Existing workflow.view; no simultaneous SSE/interval duplicate refresh |

Inventory: 291 source controls in 50 files.
