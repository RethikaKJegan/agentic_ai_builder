# Design

Tool-enabled children use a bounded JSON protocol: tool with tool_id and inputs, or finish with output. Each turn consumes the child model budget; each connector call consumes workflow and child tool budgets. Reuse one authorization/timeout/approval helper for graph and delegated tools. Persist tool intent and handoffs before calling outside the transaction; recheck run/revision/grants before accepting output. No automatic connector retries.

Workflow tool references and child capabilities are resolved by Registry as before. Do not materialize a fixed graph tool node when a dynamic child owns the tool. Model contexts contain only safe tool descriptions and schemas. Existing approval and destination checks apply to delegated writes; missing approval fails rather than granting access. Tests exercise actual GoogleSheetsConnector with mocked HTTP transport and bounded CrewAI model decisions, plus access denial, revocation, budget and connector failures.
