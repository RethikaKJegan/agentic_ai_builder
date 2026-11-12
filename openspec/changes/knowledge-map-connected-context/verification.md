# Connected-context verification

Frontend-only overlay in `knowledge-context.ts` and KnowledgeMap. Verified executed
concepts are solid green. Their direct incoming/outgoing neighbours use light green,
a dashed border and “Connected context · usage unverified”. Context includes only
one hop and follows the selected workflow step. Context appears in workflow/full
views, obeying search and module visibility. The inspector explains the connection
and explicitly states that it does not establish concept or relationship usage.
Recorded usage arrays, execution counts, relationships and backend data are unchanged.

Validation:
- 33 focused context/map/evidence adapter tests passed.
- TypeScript and changed-file ESLint passed.
- Isolated production build passed: `LtbYKT2vRr7Z-2RqnurvD`.
- Six production-artifact browser journeys passed: three generic tenants on
  desktop/mobile, checking context labels and unchanged execution counts.
- Shared-contract validation, strict OpenSpec and diff whitespace checks passed.

Deployed after explicit user approval; see [deployment](deployment.md). Public
checks passed for all three accounts and four hosted browser journeys passed.
The checked Simpsons workflow displayed one executed node and 11 context nodes.
Backend source hashes/process IDs and configuration hashes were preserved.
Private candidate/recovery artifacts are under
`.local/knowledge-map-connected-context-20261111/`.
