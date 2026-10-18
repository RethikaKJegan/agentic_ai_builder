## Implementation
- [x] Add deterministic capability selection and safe database compilers.
- [x] Integrate execution, strict source checks and bounded evidence.
- [x] Add additive physical-plan contracts and Questions UI evidence.
## Verification
- [x] Verify equivalence, rejection paths and existing regressions.
- [x] Verify real database queries, frontend checks and browser behavior.
- [x] Record verified scope and deployment evidence.

Evidence: docs/cloud-query-pushdown-phase4.md. 108 backend tests, 47 focused
frontend/domain tests, types, scoped lint, isolated production build, two browser
fixtures, contracts and strict OpenSpec passed. Public desktop/mobile acceptance
returned 830 orders using PostgreSQL pushdown. Cross-database early aggregation
is explicitly deferred; average/division and unsupported operations retain the
bounded application executor. No contributor acceptance is inferred.
