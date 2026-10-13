## Implementation
- [x] Add Phase 2 setup, mail metadata and durable polling.
- [x] Implement quotation extraction, arithmetic and qualification checks.
- [x] Implement scoped simulation award/PO authority, submission and tracking synchronization.
- [x] Add Calendar milestones and Phase 2 UI status.
- [x] Run focused offline lifecycle/quote tests and UI checks; do not start services.

Evidence: two offline Phase 2 tests pass through native planning/publication,
bounded CrewAI extraction, sender matching, delivered-cost selection, automatic
simulation awards/POs, tracking/Calendar writes and restart reuse. Eight affected
frontend tests, TypeScript and scoped ESLint pass. Shared contracts and strict
OpenSpec validation pass. No live Google/model verification or service start is
claimed. Real compliance verification and fulfilment remain outside this slice.
