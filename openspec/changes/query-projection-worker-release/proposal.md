# Correct duplicate query projections and worker completion leases

The actual failed Simpsons run selected one field twice; typed-plan validation
correctly rejected duplicate output columns. Separately, completed worker calls left
execution leases behind, producing an unrelated recovery wait message. The hosted
active-standby worker also forces concurrency=1 despite an available pool setting.

Canonicalize only repeated projected field IDs in model-generated data query output,
preserving first-seen order and all source IDs, filters, metrics and scope checks.
Release a finishing worker's own lease after its advance call exits, without stealing
another owner's lease or bypassing uncertain-action reconciliation. Allow the existing
runtime pool setting in active-standby mode, and set two slots for hosted accounts.
No active workflow will be cancelled or preempted; capacity bounds still apply.

Further tracing found an unrelated contact field from another dataset in the same
query. Validate generated plans against their supplied metadata before source dispatch;
never silently drop foreign fields. Permit one validation-feedback correction only
within a new automatic draft's explicit two-call budget, splitting its existing token
and cost caps between attempts. Invalid correction stops without source execution.
Existing reviewed workflows and explicit submitted budgets are not increased.
