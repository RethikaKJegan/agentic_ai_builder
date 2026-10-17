## Implementation
- [x] Render dataset cards with columns and labelled field-to-field edges.
- [x] Add bounded viewport, zoom controls, fit and pointer panning.
- [x] Verify focused regression, types, lint, contracts, build and desktop/mobile browser behavior.

Verification: six focused component tests, TypeScript, scoped ESLint, shared contract validation, strict OpenSpec validation and isolated production build passed. Desktop/mobile production fixture browser flows passed, including zoom, fit, panning, column inspection and existing review/description persistence. The public deployed app passed read-only desktop/mobile zoom/fit/overflow checks with 11 datasets and 88 fields and no page errors. Existing map limit of 24 datasets retained. No API, inference, review or notification behavior changed.

Deployment: frontend service only; prior build retained at `.local/ui-rollbacks/detailed-relationship-map-20261017/.next`. Screenshots: `frontend/test-results/detailed-map-live-desktop.png` and `frontend/test-results/detailed-map-live-mobile.png`.
