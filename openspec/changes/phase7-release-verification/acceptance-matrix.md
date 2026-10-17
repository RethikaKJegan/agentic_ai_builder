# Acceptance matrix

| Requirement | Evidence | Scope |
|---|---|---|
| Outdated controls and current lifecycle | frontend/e2e/api-integration.spec.ts; baseline.spec.ts; phase3.spec.ts | automated |
| Public origins, proxy, expired/missing session, CSRF | tests/test_phase1_security.py; frontend/src/api/phase1-proxy.test.ts; proxy.test.ts; session-recovery.test.ts; e2e/session-recovery.spec.ts | automated and live read-only |
| Settings/integration failure and honest verification | tests/test_phase3_actions.py; frontend/src/api/phase3-actions.test.tsx; e2e/phase7.spec.ts | automated |
| Concurrent edits and exact revisions | tests/test_phase5_state.py; test_phase2_postgres_concurrency.py; e2e/phase5.spec.ts | SQLite and actual PostgreSQL |
| Database contention and transactions | tests/test_phase2_reliability.py; test_phase2_postgres_concurrency.py; test_overview_contention.py | automated |
| Activation rollback and retry identity | tests/test_lifecycle.py; test_phase2_reliability.py; test_phase3_actions.py | automated |
| Worker interruption/leases/trigger deduplication | tests/test_phase2_workers.py; test_lifecycle.py; test_runtime.py; test_postgres_backend.py | automated |
| Runtime approvals and exact gate roles | tests/test_runtime.py; test_phase6_runtime.py; e2e/phase6.spec.ts | automated |
| Simulation versus real execution | frontend/e2e/phase7.spec.ts asserts unavailable simulation does not start a run; separate real isolated execution | simulation unavailable; distinction tested |
| Desktop/mobile graph, history and communication | frontend/e2e/phase4.spec.ts; phase6.spec.ts; phase7.spec.ts; communication/delegation/project suites | automated |
| Complete edited-workflow release journey | frontend/e2e/phase7.spec.ts | real isolated APIs/CrewAI, offline model/provider transports; explicit test operator Registry acceptance |
| Public production authenticated lifecycle | Google Workspace configuration deferred by user | unexecuted; release blocker |
| Side-effect-free product simulation | No supported runtime simulation endpoint exists | unavailable; release blocker |
| Live business mutations/provider delivery | Not submitted during Phase 7 smoke | unexecuted; no external effects claimed |

Mocked visual suites (agent-communication, delegated-tools, dynamic-delegation, multitask-delegation, project-agent-communication, sheet-access, slack-gmail, workflow-traces) use explicitly intercepted API fixtures. Their passing result is UI evidence, not live provider integration evidence. Actual Python runtime and isolated API journey tests separately exercise execution, Registry policy, leases and connector behavior.
