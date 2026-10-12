- [x] Add an isolated live example runner and persist safe run evidence.
- [x] Execute real model and GitHub calls, verify overlap and combined output.
- [x] Validate the change and record results and limits.

Live verification: scripts/test_live_delegation.py completed run run_4b3102485f88475fa26c7472e42b8c1c using seven real bounded model calls and one actual GitHub REST read. The master returned continue while the delegated tool result was outstanding, then combined the draft with the specialist findings. Returned repository facts matched the live source: octocat/Hello-World, archived=false, default_branch=master. The model identified the supplied archived/main claim as contradicted. Full source facts, decisions, handoffs, final output and instrumentation are saved in .local/live-delegation-example/evidence.json.

Synchronization intentionally holds the tool result until the independent master turn completes; model/tool responses are real and no decisions or findings are mocked. Isolated temporary storage is cleaned after evidence capture. No published workflow, operator backend process, credentials or repository data was changed. Contracts, strict OpenSpec validation and git diff --check pass. This run verifies one read-only GitHub scenario; it does not certify every possible tool or model task.
