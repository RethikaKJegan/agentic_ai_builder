> Deployment update: [now deployed with live verification](deployment.md). The local-only status below records pre-deployment testing.

# Verification — 12 November 2026

Implemented locally in agentic-ai-builder. No deployment, service restart, live workflow mutation, external delivery or paid model validation was performed.

## Passed

- Frontend production build, TypeScript check and full ESLint.
- Final focused frontend packet: 59 tests across KnowledgeMap, orchestration, workflow knowledge and knowledge context. Includes both Simpson/Subway unrelated-module exclusion and automation loading only after selecting Background with the current workflow ID.
- Additional focused composition/reliability/review frontend packet: 53 tests passed (overlapping orchestration/knowledge coverage).
- Four isolated Playwright desktop/mobile scenarios across Simpson/Subway workspace fixtures: duplicate, reload persistence, independent rename, rejected rename/retry, delete cancellation/deletion, retained copy, hidden redundant sections, no page errors or horizontal overflow. Browser API responses are controlled fixtures, not live company acceptance.
- Overview routing/API, knowledge routing, durable automation and new presentation packet: 77 backend tests passed.
- Connected action plans and new presentation packet: 51 backend tests passed (five new tests overlap the 77-test packet).
- Investigation jobs: 13 tests passed after updating the expected generated display title while asserting the original objective remains unchanged.
- Final new presentation-only rerun: five tests passed, including bounded fallback titles, connected/capability and legacy duplicate integrity/idempotency, permission denial, and workflow-scoped automation pagination/owner exclusion.
- Earlier composition/presentation/title regression packet: 67 tests passed; its five old full-prompt expectations failed and were corrected and verified in the 13-test investigation-jobs rerun above.
- Shared contract schemas/fixtures and strict scoped OpenSpec validation.
- git diff --check.

Original objective text is preserved. Existing manual names take precedence. Old workflows get a deterministic concise presentation fallback without rewriting history or invoking a model on list load. New model interpretation requests a 3–4 word title before planning; an offline/unavailable/invalid title uses the bounded fallback. Real OpenAI title quality has not been tested with paid/live calls.

Screenshots are local under .local/workflow-presentation-{simpsons,subway}-{desktop,mobile}.png. The mobile Subway screenshot was visually inspected.

Concurrent evaluator-wrapper/recovery edits appeared in the shared workspace during this task, including a workflow_title forwarding method. Those unrelated edits and their OpenSpec/test files were preserved; this task did not change their behavior or claim their implementation.
