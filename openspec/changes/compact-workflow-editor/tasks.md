- [x] Compact header and secondary details; remove outline UI.
- [x] Correct viewport sizing and initial graph fitting.
- [x] Verify types, lint, focused tests, build and desktop/mobile read-only flows; deploy.

Verification: strict frontend types, scoped ESLint, 14 focused procurement tests, shared contracts, strict OpenSpec and diff checks passed. Production candidate built in isolation and deployed with rollback `.local/ui-rollbacks/compact-20261017-155255`. Public read-only checks at 1366×768, 1920×1080 and 390×844 passed: outline absent, details drawer and setup dialog available, Design/Hierarchy/Execution accessible, underlying graph initial scale 1, no mobile document overflow, zero browser page errors. API and worker remained active and were not restarted. No workflow mutations or emails were triggered.

A broader existing phase4-journey suite also ran: three failures remain from collapsed LifecycleJourney visibility expectations and missing ResizeObserver in its hierarchy fixtures; these were outside this scoped presentation patch. The focused procurement suite passed.
