# Original-plan Phase 5: database workflow integration

Connect trusted database metadata/graph context, bounded queries and reviewed CRUD
to the existing planner, Registry, graph runtime and dynamic specialists. Preserve
canonical v1 contracts and add an explicit database-workflow metadata/tool contract.
Show selected sources/planned operations in Configuration and actual operations,
results, approvals and handoffs in Execution. Existing Google connectors compose
through the same graph; unavailable providers remain explicit, never simulated.

Writes use a prepare tool followed by a fixed graph execute tool with an immediate
human approval gate. Dynamic specialists can read/query/prepare, but cannot commit
writes inside a delegated model turn. Bind every operation to its originating run,
revision and concrete immutable request. Revalidate current owner authority and
source scope before invocation; uncertain effects never retry automatically.

Implement and verify locally using disposable databases and explicit offline model/
Google fixtures. Do not deploy, restart services, change live policy or mutate cloud
records during implementation.
