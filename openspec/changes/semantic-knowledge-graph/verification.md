# Semantic Knowledge graph verification — 18 October 2026

Scoped implementation replaces graph navigation with one semantic Knowledge graph,
retains structural evidence services, adds bounded actual-record reads, and supplies
current semantic context to source selection and workflow validation.

Evidence in `.local/semantic-kg/` (overlapping suites; do not add totals):
- `backend-final-semantic.log`: 53 passed, semantic/retrieval/relationship/legacy HTTP regressions.
- `backend-execution.log`: 86 passed, 3 skipped, query/workflow/native records/job regressions.
- `backend-guard.log`: 19 passed, including default-off extraction at provider and job boundaries.
- `frontend-final.log`: 85 passed across 13 files; focused UI contracts and proxy behavior.
- Production build, TypeScript, lint, shared contracts/generated drift and strict OpenSpec passed.
- Initial browser run passed 24 existing query/job/CRUD/workflow/preview scenarios.
- `browser-final.log`: 10 passed, desktop/mobile semantic review, actual-record forms and single/combined-source previews. Two earlier records tests used exact label locators that included option text; corrected to accessible combobox roles. No product change was required for that selector correction.
- Isolated verified production build: `s3UuI6ax0MMm4xtwwg4RX`.

Synthetic fixtures and local native database tests validate execution mechanics;
they do not establish cloud dataset contents or semantic correctness of a live model.
No external email, Calendar action, cloud write or live inference was executed by checks.

Live extraction remains disabled. Automatic approval review rejected sending private
schema metadata to the configured OpenAI destination without explicit approval.
Both worker/request and provider gates require explicit operator activation; tests
verify no SDK client/call is created while disabled. Schema-only activation and a
live model quality check remain pending owner authorization. Metadata discovery,
manual semantic review, record reads and source previews work independently.

Deployment outcome is recorded separately in `.local/semantic-kg/activation/result.json`
when the reversible activation and health checks finish.

Activation passed: all services active, verified build live, 385 prior static assets retained, configuration hashes unchanged. Live metadata preview selected the products dataset from 12 saved datasets. `live-browser.log` passed desktop/mobile single-KG and record-form checks with zero page errors; mutation/external requests were blocked. No live record read or model call was performed.

## Authorized live activation — 18 October 2026

The owner explicitly authorized the previously described schema-only payload to
api.openai.com using configured gpt-5.6-luna, including automatic extraction on
schema updates. Only BUILDER_KG_SEMANTIC_INFERENCE_ENABLED was enabled in .env;
API/worker restarted gracefully and all three services are active. The initial
private environment backup is mode 0600; no credentials or write policies changed.

Live job completed ready, current graph not stale, no reported error. Of 10
structural relationships, 6 have inferred predicates with validated evidence
references and 4 remain ambiguous. This verifies live proposal publication and
fail-closed ambiguity; it does not verify the business truth of inferred labels.
No business records were submitted to the extractor, and no database write,
email or Calendar action was executed by activation checks. Earlier pending
activation notes describe the state before this explicit authorization.
