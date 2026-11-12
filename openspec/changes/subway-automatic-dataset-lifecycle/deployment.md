# Subway automatic dataset lifecycle deployment

The user explicitly authorized deployment to https://praxi.bellcorpstudio.com/ after verification.

Candidate: `/home/raf/agentic-ai-builder/.local/subway-dataset-lifecycle-release-20261112/app`.

Release SHA-256: `ff9c794045bbd9ff4fffee6a255ae8a8b738e44d2e77c4ca870b77d0b353e9d3`.

The candidate preserves the prior isolated Subway release and changes only seven scoped existing runtime/API modules plus the new lifecycle module and two test files. The existing deployed provider wrapper is retained. Shared service source and frontend build are untouched.

The dedicated Subway configuration enables `BUILDER_SUBWAY_DEMO_DEFAULT_ENABLED=1`. The original demo opt-in remains enabled. Startup reuses and validates the existing records/ontology, adds scoped lifecycle metadata/audit/archive tables and sets the active pointer. No new production demo version is created.

Target dataset remains `subway-demonstration-v1`, revision 1, SHA-256 `e29d250b172a64701e3af577a8fa4c5db77d5662e68f3c1ddfd1bfeda128f80c`; associated ontology is `bov_subway_demonstration_v1`, typed rule version `subway-demo-procurement-v1`. Existing approved schedules and saved workflows retain their source contracts.

The task-owned override is `/etc/systemd/system/agentic-builder-subway.service.d/zzzzzzz-subway-dataset-lifecycle-release.conf`. Only Subway may restart. The prepared consistent backup and original backend config are private under `.local/subway-dataset-lifecycle-20261112/`. Preservation compares all existing demo/historical data, source/Google credentials, snapshots, ontology/package versions, workflow/run history, receipts and schedules. Only routine source-profile timestamps are normalized. Previous source hashes and unrelated service PIDs are checked before and after activation.

Rollback restores `backend-before.env`, removes only this new override, reloads systemd and restarts only Subway. The earlier persistent-demo override remains. Retain added lifecycle metadata/audit and existing records; rollback requires no destructive data cleanup.

Deployment passed at **19:14 IST on 12 November 2026**. The effective systemd WorkingDirectory and `/proc/<MainPID>/cwd` match the exact candidate above. Startup reused the original records/ontology, registered the active v1 pointer and enabled automatic defaults. All protected pre-existing rows and configuration/key checks passed immediately after restart; shared running source hashes and unrelated service PIDs remained unchanged. Public no-prefix acceptance completed at **19:16 IST**. [Open the completed Subway report](https://praxi.bellcorpstudio.com/app/workflows/investigate?connected=1&composition=composition_71e6729c7487d089f03f3e05&run=run_2f9d1d61cb2e42c1897529e8eb2b0533). Run `run_2f9d1d61cb2e42c1897529e8eb2b0533` has automatic source selection, the original v1 dataset hash, 470 deterministic outcomes, actual Knowledge Map usage and a labeled report. Public session/tools/worker-health/query/lifecycle checks pass; real-current source substitution is rejected. Final existing-row, source-key, code-hash and unrelated-PID comparisons passed after execution. Existing live schedules were not created, changed or rebound by hosted acceptance.
