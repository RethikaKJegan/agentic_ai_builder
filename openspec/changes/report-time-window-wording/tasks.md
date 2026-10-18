- [x] Accept common meeting-window wording and verify regression cases.
- [x] Validate contracts and scoped OpenSpec, then reload services and check readiness.

21 planner tests pass, including the supplied within wording through actual
compilation, six equivalent window forms and invalid/incomplete windows.
Contracts, strict scoped OpenSpec and diff checks pass. Backend/worker reloaded;
session HTTP 200 and current RuntimeWorker ready. No model requests, workflow
execution or Google writes were needed for verification. Retry generation with
the same prompt; the historical failed planning job remains unchanged.
