# Optional cumulative token and cost budgets

The inventory run can finish research but exhaust its coordinator's cumulative
token allowance before synthesis. The operator requested removing the backend
usage caps. Add an explicit server-owned opt-out for cumulative token and cost
enforcement. Preserve finite per-request token capacity, model/tool call counts,
retry limits, deadlines, Registry authorization, schemas and action approvals.
Continue recording reservations and confirmed usage. Existing revisions need no
mutation or republishing. Defaults remain enforced for other deployments.

No shared contracts change. Enable the opt-out in this deployment only after
offline verification; do not run workflows or execute Google actions.
