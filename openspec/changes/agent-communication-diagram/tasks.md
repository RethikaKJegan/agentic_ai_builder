- [x] Record bounded run-scoped handoff evidence and invocation UUIDs.
- [x] Build canonical/local hierarchy diagram with stable UUIDs and exact revision selection.
- [x] Add clickable agents/connections, mobile access and trace inspection.
- [x] Verify identity stability, data/control distinction, retries, evidence isolation and desktop/mobile browser flows.

Verification: 161 backend tests (plus final 51-test runtime rerun), 77 frontend tests, ESLint, production build/type checks, shared contracts and strict OpenSpec pass. All four trace/communication desktop/mobile browser flows pass, including historical revisions, UUID stability, polling, result correlation and parent relationships. Real local workflow smoke check passed on desktop/mobile with no browser errors; fresh Closed-ticket run run_090bd683558a44928495f6f7687f6055 captured two handoff UUIDs and matched receiver outputs. Model and email steps were skipped. Master/sub-agent exchange was separately verified through the real runtime with registered offline adapters and through browser fixtures; no live hierarchy workflow currently exists in the server collection.
