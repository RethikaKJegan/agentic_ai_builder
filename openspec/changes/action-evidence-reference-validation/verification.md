# Evidence-reference validation — 10 November 2026

## Confirmed defect
The hosted error was ACTION_CONTENT_UNVERIFIED during generation. Inspection confirmed that evidence-reference validation happened after the try/except containing bounded planner correction. Unlike output bindings, citations of existing action results did not materialize dependency edges. The rejected production proposal was not retained in available diagnostics; its exact offending reference is unknown. Controlled proposals reproduce both failure classes without asserting they are the original proposal.

## Correction
Automatic-input planning now turns citations of known distinct actions into explicit dependencies, preserving pinned-evidence identities. Cycles and conditional dependencies still fail existing graph checks. Unknown and self references are retained for strict rejection, never silently discarded or promoted into evidence.

Evidence-reference validation now runs inside the existing guarded planning path before compilation. Diagnostics expose the action and invalid/allowed reference identities without runtime records. Generated plans can receive one correction using the existing shared planning-call budget; explicit plans and repeated invalid proposals remain rejected. Guidance distinguishes action/evidence IDs from dataset, field and capability IDs. Existing query-envelope normalization, selected-account resolution, exact-payload approvals and shared contracts are unchanged.

## Evidence recorded so far
- Two controlled reproductions failed before implementation and passed afterward.
- The durable query/report/Sheets/email runtime passes with a newly materialized evidence edge using fixture-only model and HTTP providers.
- User's exact prompt with controlled deliberately invalid reference proposals passes against copied Simpson data after one bounded correction; selected account and exact-payload approval remain pinned. This is not evidence of live OpenAI interpretation.
- Six baseline/candidate startup/auth/API rehearsals passed against copied operator, Simpson and Subway stores with networking and workers disabled and protected-record guards enabled.
- Fresh main/Simpson/Subway backups passed quick_check, with 53 configuration/credential files and nine provider-state files verified.
- Contract schemas/fixtures and strict OpenSpec validation passed.
- Final scoped regression suite: 164 passed. Additional durable runtime evidence-edge test: one passed.
- Hosted activation, six read-only browser journeys, service health and preservation all passed; see deployment.md.

An initial local test parameter named reference shadowed an existing fixture; it was renamed and the run restarted. No production validation was loosened. No live model call, live workflow submission or real email/Sheets effect has been performed for verification.
