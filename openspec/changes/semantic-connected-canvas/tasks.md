- [x] Add key-backed identifier resolution and evidence-backed source membership to the existing canvas.
- [x] Improve layout/labels and preserve original relationship review and inspection controls.
- [x] Verify zero isolated nodes and one connected component on current live metadata, filter scope and ambiguous references; verify API input unchanged.
- [x] Run relevant UI/domain tests, types/lint/build and desktop/mobile browser checks.
- [x] Deploy frontend only with rollback and verify live graph/unchanged workflow bindings.

Evidence: docs/semantic-intelligence-canvas.md and .local/semantic-connected-canvas/{connectivity-verification.json,isolated-browser-verification.json,live-browser-verification.json,live-http-verification.json}. 22 focused tests/types/lint/build/contracts/scoped OpenSpec pass. Live graph has 32 reachable nodes, 47 edges and zero isolates on desktop/mobile; original API graph and workflow scope/steps/approval gates unchanged. Frontend only deployed; backend/worker/source data untouched.
