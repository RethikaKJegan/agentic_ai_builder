# Design

Reuse DataQueries catalogue/validation/persistence and DataQueryJobs immutable job
snapshots. A data.plan_query CrewAI action emits a self-contained typed query,
validated by a workflow_data_query Registry connector using current account
metadata. No customer routing or hidden model calls are introduced.

The workflow pins a metadata fingerprint. Executable plans are prepared separately
for each run/node identity. Job retry keys include account/run/node identity;
existing jobs are checked before preparing another plan. Job wait exceptions
persist progress, release the worker lease and leave dependencies pending. Only
operator-installed read-only durable query connectors can recover interrupted
submissions; all uncertain external effects retain their existing recovery guard.
Polling reserves the query tool budget once, while normal Registry/current access
checks run every time. Source job limits and workflow/agent duration limits apply.

Reports receive the actual typed query result, with matched count, display limit,
source revisions, execution time, filters, warnings and join checks. Sampled
projection is rejected as population evidence. Existing content/receipt/approval
bindings connect report, Sheets and mail. Selected Google account resolution,
including explicitly requested "email me", remains in existing goal_inputs.

Recurring queries additionally require an exact query const in existing automation
consent, checked before reads. Fresh executable plans use that reviewed meaning
and current mapping fingerprint; mapping changes stop execution. This does not
add natural-language schedule creation or new consent UI: those remain separate
integration work, and current scheduling continues through DurableAutomation.
