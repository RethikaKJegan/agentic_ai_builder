# Delegated tool access

Concurrent subagents currently cannot check external facts because their execution path has no connector dispatch. Add an application-managed tool decision loop using the exact child agent's reviewed Registry grants, existing connectors and cumulative runtime budgets. The master keeps working while the child requests a tool, receives actual tool output and synthesizes its findings.

Keep selection generic. Google Sheets is an existing connector, not a hardcoded verification rule. Do not expose credential or authorization references to models or traces.
