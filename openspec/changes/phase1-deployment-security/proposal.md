# Phase 1: production routing, Google Workspace authentication and API proxy

Confirmed: live launcher enables global development-admin sessions; origin settings bypass the launcher's merged environment; proxy defaults to test API port 8011 and aborts planning before the provider deadline.

User explicitly deferred Google Workspace production authentication. Do not implement or configure Google login in this phase. Fail closed for production startup until a later authenticated deployment is implemented. Restrict development auth to explicit local/test environments and loopback origins. Preserve canonical v1 contracts and existing working-tree database edits.

Validate public origin exactly, retain CSRF controls and signed provider webhooks, bind backend only to loopback, and use live port 8000 with explicit test port 8011. Harden the proxy's upstream configuration, status/error contracts, bounded bodies, correlation, cookies, SSE and timeout handling. Add durable asynchronous planning with scoped job status, cancellation and result retrieval; preserve synchronous compatibility.

Production smoke/login requires operator-owned Google OAuth configuration and deployment access; do not claim readiness from offline tests.
