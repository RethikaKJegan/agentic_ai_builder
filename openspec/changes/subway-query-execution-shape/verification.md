# Query execution verification

Saved run `run_9cbdb64a52b6442896592bb9d30f6219`, workflow `cw_8f3ef46a3cbb76d012c7f458`, failed at `plan_largest_orders` with `AGENT_OUTPUT_INVALID`. Query reads and email actions remained pending. The workflow permitted one call per query agent and zero recovery retries. Historical rejected output was not persisted, so its exact defect cannot be established retrospectively.

The saved task requests projected order details, currency-label resolution through a declared join and a complete matching count. Its prior model schema accepted invalid mixed projection/aggregate queries and arbitrary field IDs. The shared CrewAI schema specialization previously handled only generic data-query catalogs and left Subway queries unconstrained.

The runtime now sends mutually exclusive detail/aggregate shapes and current catalog identities to the model. It explains that detail counts come from `coverage.matched_records`, aggregates are per group, explicit filters stay intact and monetary values retain their currencies. Only redundant generated projections already present in group_by are canonicalized. Direct query validation, source authorization, joined-field validation, budgets, retries, saved workflows and source records retain their existing authority.

Provider enum/string/byte bounds are checked; unusually large catalogs retain mode constraints and strict execution validation. Safe `agent.output_rejected` events retain trusted validation rules without rejected query values or model prose.

Offline replay used the actual saved catalog and verified joined detail and vendor-by-currency aggregate queries; mixed detail/aggregate output and foreign fields were rejected by the new model contract. The replay used no model calls, source queries or email actions. Separate controlled-model tests exercised actual CrewAI and GraphRunner execution with complete synthetic source scans and pagination.

A live isolated model replay was rejected by automatic approval review because it could transmit tenant data to a paid provider and retain raw output. That call was not performed or bypassed. Validation therefore does not establish the response quality of a fresh live model invocation or actual email delivery.

Private deployment evidence and exact rollback sources: `.local/subway-query-execution-20261112/`.

Validation completed: 224 unique tests passed across focused query contracts, actual offline CrewAI/runtime execution, shared runtime/model protocol, reporting, recovery/worker handling, native Subway query execution, routing/selection and Simpsons isolation. One in-memory OpenTelemetry test initially ran with OTEL_SDK_DISABLED=true and failed; it passed with the test-required SDK enabled. Framework deprecation warnings remain. Contracts, generated UI contracts, OpenSpec strict validation and whitespace checks passed.

Deployment completed: only agentic-builder-subway restarted. Authenticated HTTPS health/tools/worker/query-list checks passed for operator, Simpsons and Subway; foreign source access remained denied. Source credentials/bindings, selected Google connections, ontology packages, automations, history and configuration were preserved. Other service process IDs and frontend build remained unchanged. No model replay, live workflow execution, business source query or email action was performed during this fix. Start a fresh workflow from Overview using the same prompt; the previous terminal failed run remains in history.
