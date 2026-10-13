- [x] Implement reviewed activation, worker routing and prompt/UI configuration.
- [x] Implement matched polling, grounded extraction and durable fulfilment events.
- [x] Implement tracking/Calendar synchronization, reminders and buyer closure.
- [x] Verify focused offline lifecycle, guard and UI tests.

Follow-up: verify the real client activation method with an injected HTTP
transport, and display an actionable frontend-reload message if a stale
development bundle has no activation method.

Evidence: native offline Phase 2-to-3 lifecycle test passes through authenticated
activation, real bounded CrewAI master/specialists, exact actor/thread matching,
three orders through supplier stages and buyer closure, 15 Activity rows,
tracking/Calendar updates, three closure notifications and restart deduplication.
Five focused real-store guard tests cover partial quantities, exception/buyer
authority, duplicate processing and buyer resolution requests. Nine affected
frontend tests, TypeScript and scoped ESLint pass. Contracts, strict OpenSpec and
diff checks pass. No services started, credentials changed or live Google/model
calls performed. Automatic fulfilment authority is simulation-only; controlled
live verification remains necessary.
