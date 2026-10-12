- [x] Record bounded observations, outputs, branch evidence and node failures.
- [x] Add run selection, live canvas statuses and clickable node trace/configuration tabs.
- [x] Verify runtime isolation/redaction, run selection, history gaps and desktop/mobile browser behavior.

Verification: 157 backend tests, 71 frontend tests, TypeScript, ESLint, production build, shared contract validation and strict OpenSpec pass. Desktop/mobile browser flows pass. Read-only smoke check of planned_82b3260b91547770 on port 3001 found 7 nodes, 2 historical runs and no browser errors. Idle live backend restarted on port 8002 to load recording code. No workflow was manually executed or email submitted by verification. Historical evidence gaps remain explicit.
