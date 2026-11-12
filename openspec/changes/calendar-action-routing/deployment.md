# Calendar action routing — deployed 12 November 2026

Release `calendar-routing-20261112-43ed19536853` is deployed to Subway and Simpsons at https://praxi.bellcorpstudio.com/.

Observed defects:

- Subway's dataset-selection gate blocked Calendar-only requests despite needing no business records.
- Event timestamp parsing did not support explicit start/end intervals or word durations such as thirty-minute; primary Google Calendar was not recognized as primary calendar.
- The question-free fallback replaced unresolved Calendar work with a report-only composition. The user's saved recurring Calendar request contained only content.prepare, so no Calendar connector was invoked.
- Configured-model verification also reproduced Calendar creation being misclassified as an incoming business-event subscription, and a model inventing an optional reminder input.

The generic fix routes source-free connected actions independently of business data/ontology requirements and restricts their capability set accordingly. Calendar creation is distinguished from incoming business events using server-resolved event facts. Explicit intervals and supported word durations resolve to trusted timezone-aware timestamps. Optional event properties are omitted when unspecified. Requested Calendar writes must remain unconditional ancestors of required completion actions; omission gets one existing bounded planner correction, then explicit failure. Unresolved Calendar requests retain clarification instead of a successful report substitute.

A reviewed same-day recurring event pins timezone, local event time and duration. Runtime resolves each date from the durable scheduled occurrence, not wall-clock worker execution or model output. Recurring consent retains the pin and checks actual event start/end against it immediately before connector dispatch. Existing account scope, Registry grants, exact-payload approval, connector validation and effect journals remain authoritative.

Verification:

- 55 tests passed directly from the actual service release: Calendar routing/parsing/execution, recurrence, generic Overview routing and receipt-aware completion.
- 52 broader source-routing, Subway intelligence, recurring integration, Calendar evidence and receipt-completion regressions passed. Counts overlap with the active-release packet.
- Ten targeted Calendar tests passed, including real native durable dispatch on two successive days, fresh event dates, exact consent/approval and duplicate prevention. Google transport was fake; no real event was created.
- Both tenants' configured models successfully interpreted the Calendar-only request and generated a real reviewable plan containing Calendar creation using exclusively synthetic fixture metadata. No business records or real Google actions were sent.
- Actual Subway and Simpsons launchers loaded the patched modules and exposed Calendar-create tools/connectors. All three connected Google accounts in each tenant advertised Calendar scopes; scope metadata alone is not proof of an actual Google write.
- Canonical contracts, generated UI mappings, strict OpenSpec and whitespace checks passed.
- Authenticated hosted endpoints, workers/services and tenant isolation passed. Protected credentials, ontology, knowledge, histories and existing automation records were preserved; periodic source-profiling timestamps were excluded from source-binding comparison. Other backend PIDs and the frontend build were unchanged.

Only `agentic-builder-subway` and `agentic-builder-simpsons` restarted. Actual code: `.local/workflow-ui-release-20261112/app`. Private verification, database snapshots and rollback source: `.local/calendar-action-routing-20261112/`.

Refresh and generate a new workflow; previous report-only compositions remain historical and do not gain unreviewed external actions. Select the connected Google account and review the Calendar action before execution. Real Google Calendar creation still requires the user's approved live test. Planning transport follows the [official Structured Outputs requirements](https://developers.openai.com/api/docs/guides/structured-outputs).
