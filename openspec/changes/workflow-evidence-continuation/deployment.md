# Hosted backend update — 11 November 2026

Deployed to https://praxi.bellcorpstudio.com/ as
`evidence-continuation-20261111-4f495edad5d6` at **1:50 PM India time**.

Four backend files changed: Overview routing, goal input defaults, action
compilation and shared planning guidance. Calendar event dates are resolved from
the planning clock; an event time no longer becomes a workflow execution timer
when the server can establish that distinction. Recoverable question-free
planning gaps now prepare a scoped evidence/limitations report with unresolved
operations explicitly deferred. They do not fabricate data or action receipts.

Verification: [195 selected regression cases across the broad run and focused
recheck](verification.md), saved-request replay, contracts, syntax, formatting and
strict specification validation. Authenticated public read-only checks passed for
operator, Simpsons and Subway. All five application services are active with no
automatic restarts. The live report present at the first deployment attempt was
allowed to complete before any service was stopped.

Consistent compressed online backups of all three account stores passed integrity
and decompression/hash verification. Configuration copies and the four-file
rollback source are retained privately under
`.local/workflow-evidence-continuation-20261111/`. Post-deployment checks confirm
history counts preserved, existing encrypted credentials unchanged, automation
records unchanged, and configuration/frontend hashes unchanged. No database
restore, frontend change or credential/configuration change occurred. The disk
space needed for release was recovered from rebuildable download caches in two
superseded release staging folders; no database backup or live data was deleted.

No paid model request, live workflow submission, email, Sheet or Calendar event
was triggered by verification. Controlled tests and saved-request replay are not
proof of a successful live model/Calendar execution. Generate a **new request**
to use the corrected planning behavior; historical blocked drafts stay preserved.

Authorization and exact-action approvals remain required. Genuine provider,
permission and unsupported-query errors are not disguised as successful actions.
