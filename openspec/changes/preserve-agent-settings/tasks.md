- [x] Preserve model temperature omission when a UI projection has not changed it.
- [x] Recognize concise inventory report wording and exact meeting intervals.
- [x] Test unchanged save/Registry binding and equivalent report prompts; retain negative cases.
- [x] Deploy and recover the affected draft without approving or executing actions.

Evidence: 29 focused frontend tests passed. Backend report/compiler, runtime, worker, cross-segment and workflow API checks: 61 passed plus 6 subtests; one unrelated existing assertion in test_safe_planner_errors_and_missing_runtime expects an empty tool list despite built-in database tool registration. No change to Registry mismatch enforcement; its edited-agent rejection test passes. Build, typecheck, lint, contracts, strict OpenSpec and diff checks passed. Desktop/mobile production-build approval smoke checks passed with mocked decisions. Frontend/backend/worker deployed. Recovered planned_ed9903c4c4972064 as revision 3 through normal planning/save/validate APIs; unresolved_requirements empty, three action gates, only expected pending approval review codes. No external action, workflow approval or publication performed.
