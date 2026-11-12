# Hosted connected-context highlighting — 11 November 2026

Deployed to **https://praxi.bellcorpstudio.com/** after explicit user approval.
Frontend build: `LtbYKT2vRr7Z-2RqnurvD`, activated at **4:20 PM India time**.

Verified execution uses solid green. Direct incoming/outgoing neighbours use light
green, a dashed border and “Connected context · usage unverified”. Highlighting
stops after one hop, follows step selection and never increases execution counts.
The inspector explains that connectivity does not establish concept/relationship
usage. Existing workflows can use the visual update after refreshing the page.

Validation: 33 focused tests, six three-tenant desktop/mobile production-artifact
browser journeys, types, lint, build, shared contracts and strict OpenSpec passed.
Public account/session/query/tool/worker checks passed for all three routes. Four
hosted desktop/mobile browser journeys passed without errors or overflow. The
checked Simpsons workflow rendered **one executed concept and 11 connected-context
concepts**. The checked historical Subway workflow had no verified executed usage,
so it correctly rendered no context highlights.

Only the frontend restarted. Backend/runtime/planner/Registry/contracts source
hashes, four backend/worker process IDs and configuration hashes stayed unchanged.
Frontend remains active with zero automatic restarts. No workflow execution, model
call or provider action was triggered. No database was changed by this UI release.
Previous static chunks and the prior complete frontend artifact are retained under
`.local/knowledge-map-connected-context-20261111/` for application-only rollback.
