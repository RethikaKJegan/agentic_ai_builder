## Implementation
- [x] Add query contracts, owned expiring plans and structured model planning.
- [x] Add bounded read adapters, validated joins and deterministic computation.
- [x] Add Questions UI with plan review, execution, evidence and errors.
## Verification
- [x] Verify backend permissions, correctness, limits, stale state and cloud boundaries.
- [x] Verify frontend types, lint, build and desktop/mobile browser flows.
- [x] Document actual supported scope and deployment evidence.

Evidence: docs/cloud-data-queries-phase3.md. 69 backend regressions, 33 frontend tests, types, scoped lint, production build, two browser fixtures, contracts and strict OpenSpec passed. Deployed browser NL query returned 830 orders on desktop/mobile; live Mongo count returned 91; all five live sales totals matched independent SQL. No contributor signoff inferred.
