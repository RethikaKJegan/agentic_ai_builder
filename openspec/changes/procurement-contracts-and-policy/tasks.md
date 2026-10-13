## Step 1 — Contracts and policy
- [x] 1.1 Define versioned procurement records and examples.
- [x] 1.2 Define state transitions, partial fulfilment and evidence guards.
- [x] 1.3 Define approval matrix, authority and stop conditions.
- [x] 1.4 Validate artifacts and confirm original files remain unchanged.

Later spreadsheet creation, persistence and orchestration are explicitly out of scope.

Verification: 14 fictional example records and a valid closed-order fixture pass; 18 invalid representations are rejected; 60 ordinary state edges, partial/hold/cancellation definitions and the reviewed default policy are checked. Original canonical schemas/fixtures pass. Both official OpenSpec 1.14.1 strict library validation passes return valid with zero issues. The CLI wrapper required newer Node; the existing validator library was used without upgrading Node or project dependencies. All 484 original tracked files retain their starting hashes. No runtime activation or provider operation occurred.
