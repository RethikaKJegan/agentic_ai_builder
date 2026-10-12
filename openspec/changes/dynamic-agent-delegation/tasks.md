# Tasks

- [x] Add delegation contract and validation.
- [x] Implement bounded persisted master decisions and dynamic child invocations.
- [x] Wire hierarchy generation and live diagram to delegation.
- [x] Verify differing input-dependent selections, repeat spawning, failures, limits, cancellation, and UI evidence.

Evidence: 173 Python tests, 78 frontend tests, build/type checks, lint, contract validation and six desktop/mobile browser scenarios pass. Actual bounded CrewAI integration uses offline transport in regression tests. Separate live model-only workflow planned_02488ce39981ef9d selected classification_specialist for run_4de7723ea0554429b82f08887cfb7360 and summary_writing_specialist for run_93e3b0565a114b558c941b54489a4ad2; both completed with delegate/finish decisions and no tools. Real live browser inspection passed for both runs on desktop/mobile with no errors. No existing published workflow was rewritten.

Additional multi-task acceptance: live run `run_c3df77212a2344d986c2c3da087fed02` completed two separate classification tasks, then delegated their results to the summary specialist. Three runtime invocation UUIDs and six handoff UUIDs were unique and correctly paired. Fixed a Dagre multigraph/cycle layout crash by placing forward dependencies separately from displayed return links; removed redundant dynamic parent links and separated task/return paths. Live desktop/mobile inspection opened every spawned task and all six handoffs with zero browser errors; desktop labels did not overlap. The captured live event regression passes on both viewports. Updated verification: 79 frontend tests, production build/types, lint and eight browser scenarios pass. Evidence: `.local/multitask-delegation-evidence.json`, `.local/multitask-browser-report.json`, `.local/multitask-uuid-desktop.png`.
