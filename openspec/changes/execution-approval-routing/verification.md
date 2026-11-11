# Verification — 10 November 2026

The saved Simpson black-smoke request `741aa177-b856-4190-9107-800192788bfd`
was blocked because its interpreted missing requirements contained only a notice
that approval was required before sending email. Its source scope and selected
self-mail destination had already been resolved.

The correction adds server-owned instructions separating execution approvals from
missing planning information, plus conservative normalization of clear execution
approval notices in question-free mode. Normalization changes only the interpreted
missing-requirements list. It does not select tools, change operations, grant scopes,
activate schedules or approve execution. Actual action contracts and runtime gates
remain authoritative. Legacy mode retains its previous handling.

Regression tests cover notices for email, spreadsheet creation/update, Calendar,
web search and combined execution. Actual missing destinations, unavailable access,
OAuth scopes, ambiguous questions, mixed statements and business approval meanings
remain unresolved. The actual faulty approval-only route reaches normal action
planning and compilation with its email approval gate and mandatory workflow review.
An unknown-recipient requirement still creates a blocked draft with no questions.

The exact saved route was replayed against a fresh private Simpson database copy.
It now prepares an immediate composed intent, preserving email_send and the scoped
account. Adding an unknown recipient still blocks preparation. Startup protected rows
were unchanged; networking and workers were disabled. No paid model, live source
execution or provider delivery was used for rehearsal.

Final test counts and hosted activation evidence are recorded in deployment.md.
Tests use controlled interpretation and provider responses. They do not certify
all possible live model wording or add unsupported tools, query operators, data
relationships or complete symptom-search capabilities. Historical blocked requests
retain their idempotent results; users should generate a new request after rollout.
